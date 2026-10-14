"""Load and check pipeline.yaml.

Every check runs here, before any network or LLM call.
Input paths are relative to the config file's folder.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

Label = Literal["EXCLUDE", "LOW", "MEDIUM", "HIGH"]
LABELS: tuple[str, ...] = ("EXCLUDE", "LOW", "MEDIUM", "HIGH")


class ConfigError(ValueError):
    """A problem in a config file."""


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LLMSettings(_Model):
    """Passed to mmore's LLMConfig."""

    llm_name: str
    provider: str | None = None
    base_url: str | None = None
    temperature: float = 0
    max_new_tokens: int | None = None

    def to_mmore(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)


class DiscoverySettings(_Model):
    config: Path


class OwnDocumentsSettings(_Model):
    folder: Path | None = None  # the ingest stage is skipped if unset or missing
    fast: bool = True
    sanitize: bool = True

    @field_validator("sanitize")
    @classmethod
    def _always_sanitize(cls, value: bool) -> bool:
        if not value:
            raise ValueError("own documents are always sanitized; remove `sanitize: false`")
        return value


class PrivacySettings(_Model):
    sanitize_config: Path
    before_screening: bool = True
    rag_privacy_config: Path | None = None


class ScreeningSettings(_Model):
    criteria: Path
    llm: LLMSettings
    min_year: int | None = None
    min_chars: int = Field(500, ge=0)
    max_chars: int = Field(60_000, gt=0)
    use_abstract_if_no_text: bool = True
    max_concurrency: int = Field(4, ge=1)


class IndexSettings(_Model):
    db_uri: str = "runs/{run_name}/milvus.db"
    db_name: str = "review"
    collection: str = "review"
    dense_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    sparse_model: str = "splade"
    include_labels: list[Label] = ["HIGH", "MEDIUM", "LOW"]
    include_own_documents: bool = True


class AskSettings(_Model):
    llm: LLMSettings | None = None  # defaults to screening.llm
    k: int = Field(6, ge=1)
    reranker: str | None = "BAAI/bge-reranker-base"


class PipelineConfig(_Model):
    run_name: str = Field(pattern=r"^[A-Za-z0-9._-]+$")
    runs_dir: Path = Path("runs")
    discovery: DiscoverySettings
    own_documents: OwnDocumentsSettings = OwnDocumentsSettings()
    privacy: PrivacySettings
    screening: ScreeningSettings
    index: IndexSettings = IndexSettings()
    ask: AskSettings = AskSettings()

    @property
    def run_root(self) -> Path:
        return self.runs_dir / self.run_name

    @property
    def ask_llm(self) -> LLMSettings:
        return self.ask.llm or self.screening.llm


def _format_errors(path: Path, err: ValidationError) -> str:
    lines = [f"Invalid config {path}:"]
    for e in err.errors():
        where = ".".join(str(p) for p in e["loc"]) or "(top level)"
        lines.append(f"  {where}: {e['msg']}")
    return "\n".join(lines)


def _resolve(base: Path, p: Path) -> Path:
    return p if p.is_absolute() else (base / p).resolve()


def load_pipeline_config(path: str | Path) -> PipelineConfig:
    """Read, check and resolve a pipeline.yaml. Raise ConfigError on any problem."""
    path = Path(path)
    if not path.is_file():
        raise ConfigError(f"Config file not found: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise ConfigError(f"Config {path} is not valid YAML: {e}") from e
    if not isinstance(data, dict):
        raise ConfigError(f"Config {path} must be a mapping.")

    try:
        cfg = PipelineConfig.model_validate(data)
    except ValidationError as e:
        raise ConfigError(_format_errors(path, e)) from None

    base = path.parent.resolve()
    cfg.runs_dir = _resolve(base, cfg.runs_dir)
    cfg.discovery.config = _resolve(base, cfg.discovery.config)
    cfg.privacy.sanitize_config = _resolve(base, cfg.privacy.sanitize_config)
    if cfg.privacy.rag_privacy_config:
        cfg.privacy.rag_privacy_config = _resolve(base, cfg.privacy.rag_privacy_config)
    cfg.screening.criteria = _resolve(base, cfg.screening.criteria)
    if cfg.own_documents.folder:
        cfg.own_documents.folder = _resolve(base, cfg.own_documents.folder)

    uri = cfg.index.db_uri.format(run_name=cfg.run_name)
    cfg.index.db_uri = uri if "://" in uri else str(_resolve(base, Path(uri)))

    _check_files_exist(path, cfg)
    return cfg


def _check_files_exist(path: Path, cfg: PipelineConfig) -> None:
    files = {
        "discovery.config": cfg.discovery.config,
        "privacy.sanitize_config": cfg.privacy.sanitize_config,
        "screening.criteria": cfg.screening.criteria,
    }
    if cfg.privacy.rag_privacy_config:
        files["privacy.rag_privacy_config"] = cfg.privacy.rag_privacy_config
    missing = [f"  {key}: {p}" for key, p in files.items() if not p.is_file()]
    if missing:
        listing = "\n".join(missing)
        raise ConfigError(f"Invalid config {path}: these paths do not exist:\n{listing}")
