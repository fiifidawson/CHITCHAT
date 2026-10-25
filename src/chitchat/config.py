"""Load and check pipeline.yaml.

Every check runs here, before any network or LLM call.
Input paths are relative to the config file's folder.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

Label = Literal["EXCLUDE", "LOW", "MEDIUM", "HIGH"]
LABELS: tuple[str, ...] = ("EXCLUDE", "LOW", "MEDIUM", "HIGH")


class ConfigError(ValueError):
    """A problem in a config file."""


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


StructuredOutput = Literal["json_schema", "json_mode", "function_calling"]


class LLMSettings(_Model):
    """A model. Passed to mmore's LLMConfig.

    Local open models: set `base_url`
    (Ollama: http://localhost:11434/v1, vLLM: http://host:8000/v1).
    Hosted OpenAI-compatible providers: also set `provider`;
    the key is read from <PROVIDER>_API_KEY.
    """

    llm_name: str
    provider: str | None = None
    base_url: str | None = None
    temperature: float = 0
    max_new_tokens: int | None = None
    # How structured answers are requested. Try json_mode or function_calling if a server
    # rejects json_schema. Not passed to mmore.
    structured_output: StructuredOutput = "json_schema"

    def to_mmore(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True, exclude={"structured_output"})


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
    llm: LLMSettings | None = None  # defaults to the top-level llm
    min_year: int | None = None
    min_chars: int = Field(500, ge=0)
    max_chars: int = Field(60_000, gt=0)
    use_abstract_if_no_text: bool = True
    max_concurrency: int = Field(4, ge=1)


DOCKER_MILVUS = "http://127.0.0.1:19530"


class IndexSettings(_Model):
    # `auto`: Milvus in Docker on Windows (Milvus Lite has no Windows build),
    # a Milvus Lite file in the run folder on macOS and Linux.
    db_uri: str = "auto"
    db_name: str = "review"
    collection: str = "review"
    dense_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    sparse_model: str = "splade"
    include_labels: list[Label] = ["HIGH", "MEDIUM", "LOW"]
    include_own_documents: bool = True


class AskSettings(_Model):
    llm: LLMSettings | None = None  # defaults to the top-level llm
    k: int = Field(6, ge=1)
    reranker: str | None = "BAAI/bge-reranker-base"


SearchMode = Literal["deep", "shallow"]

# Defaults for `chitchat search`. Override any field under `search.deep` or `search.shallow`.
DEFAULT_PRESETS: dict[str, dict[str, Any]] = {
    # A fast look at what exists: 1 to 3 focused queries, abstracts only.
    "shallow": {
        "clarifying_questions": 0,
        "min_categories": 1,
        "max_categories": 3,
        "max_concepts_per_category": 4,
        "max_synonyms": 5,
        "max_results": 10,
        "max_pages": 1,
        "download_pdfs": False,
    },
    # A thorough search for a review: clarifying questions, several angles, full text.
    "deep": {
        "clarifying_questions": 4,
        "min_categories": 3,
        "max_categories": 6,
        "max_concepts_per_category": 4,
        "max_synonyms": 8,
        "max_results": 25,
        "max_pages": 2,
        "download_pdfs": True,
    },
}


class SearchPreset(_Model):
    clarifying_questions: int = Field(ge=0, le=8)
    min_categories: int = Field(ge=1)
    max_categories: int = Field(ge=1)
    max_concepts_per_category: int = Field(ge=1)
    max_synonyms: int = Field(ge=0)
    max_results: int = Field(ge=1)
    max_pages: int = Field(ge=1)
    download_pdfs: bool
    sources: list[str] = ["openalex", "europepmc", "arxiv"]


class SearchSettings(_Model):
    mode: SearchMode = "deep"
    llm: LLMSettings | None = None  # defaults to the top-level llm
    deep: SearchPreset = Field(default_factory=lambda: SearchPreset(**DEFAULT_PRESETS["deep"]))
    shallow: SearchPreset = Field(
        default_factory=lambda: SearchPreset(**DEFAULT_PRESETS["shallow"])
    )

    @field_validator("deep", "shallow", mode="before")
    @classmethod
    def _fill_defaults(cls, value: Any, info: Any) -> Any:
        """Only the fields you set override the defaults."""
        if isinstance(value, dict):
            return {**DEFAULT_PRESETS[info.field_name], **value}
        return value

    def preset(self, mode: str) -> SearchPreset:
        return self.deep if mode == "deep" else self.shallow


class AnswerSettings(_Model):
    """The multi-agent loop that answers the original question at the end of a run."""

    question: str | None = None  # used when the run has no search plan (e.g. --predefined)
    llm: LLMSettings | None = None  # defaults to the top-level llm
    max_rounds: int = Field(3, ge=1, le=6)
    k_per_query: int = Field(6, ge=1)
    max_evidence_chars: int = Field(24_000, gt=1000)


class EvaluateSettings(_Model):
    judge_llm: LLMSettings | None = None  # defaults to the top-level llm; another family is better
    baseline_k: int = Field(10, ge=1)


class PipelineConfig(_Model):
    run_name: str = Field(pattern=r"^[A-Za-z0-9._-]+$")
    runs_dir: Path = Path("runs")
    discovery: DiscoverySettings
    own_documents: OwnDocumentsSettings = OwnDocumentsSettings()
    privacy: PrivacySettings
    # The one model every LLM step uses, unless a section sets its own `llm`.
    llm: LLMSettings | None = None
    screening: ScreeningSettings
    index: IndexSettings = IndexSettings()
    ask: AskSettings = AskSettings()
    search: SearchSettings = SearchSettings()
    answer: AnswerSettings = AnswerSettings()
    evaluate: EvaluateSettings = EvaluateSettings()

    @model_validator(mode="after")
    def _needs_a_model(self) -> PipelineConfig:
        if self.llm is None and self.screening.llm is None:
            raise ValueError("set a model under `llm:` (see configs/models/ for examples)")
        return self

    @property
    def run_root(self) -> Path:
        return self.runs_dir / self.run_name

    @property
    def main_llm(self) -> LLMSettings:
        llm = self.llm or self.screening.llm
        assert llm is not None  # checked when the config loads
        return llm

    @property
    def screening_llm(self) -> LLMSettings:
        return self.screening.llm or self.main_llm

    @property
    def ask_llm(self) -> LLMSettings:
        return self.ask.llm or self.main_llm

    @property
    def search_llm(self) -> LLMSettings:
        return self.search.llm or self.main_llm

    @property
    def answer_llm(self) -> LLMSettings:
        return self.answer.llm or self.main_llm

    @property
    def judge_llm(self) -> LLMSettings:
        return self.evaluate.judge_llm or self.main_llm


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

    if cfg.index.db_uri == "auto":
        cfg.index.db_uri = (
            DOCKER_MILVUS if sys.platform == "win32" else str(cfg.run_root / "milvus.db")
        )
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


def shadowed_keys(environ: dict[str, str], env_file: Path) -> list[str]:
    """API keys set in the environment AND in .env with a different value.

    The environment wins, because load_dotenv never overrides. Returns names only.
    """
    if not env_file.is_file():
        return []
    from dotenv import dotenv_values

    return [
        name
        for name, value in dotenv_values(env_file).items()
        if name.endswith("_API_KEY") and value and environ.get(name) not in (None, "", value)
    ]
