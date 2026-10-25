from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from chitchat.config import ConfigError, load_pipeline_config


def _edit(path: Path, **changes) -> None:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    for dotted, value in changes.items():
        node = data
        *parents, last = dotted.split("__")
        for key in parents:
            node = node[key]
        node[last] = value
    path.write_text(yaml.safe_dump(data), encoding="utf-8")


def test_example_config_loads(project: Path) -> None:
    cfg = load_pipeline_config(project / "pipeline.yaml")
    assert cfg.run_name == "humanitarian-llm-2026"
    assert cfg.run_root == project.resolve() / "runs" / "humanitarian-llm-2026"
    assert cfg.discovery.config.is_file()
    # `auto`: Docker on Windows, a Milvus Lite file in the run folder elsewhere.
    assert cfg.index.db_uri in ("http://127.0.0.1:19530", str(cfg.run_root / "milvus.db"))
    # One local open model for every step.
    assert cfg.screening.llm is None
    assert cfg.screening_llm.to_mmore() == {
        "llm_name": "qwen3.5:9b",
        "base_url": "http://localhost:11434/v1",
        "temperature": 0,
    }
    assert cfg.ask_llm == cfg.search_llm == cfg.answer_llm == cfg.judge_llm == cfg.main_llm


@pytest.mark.parametrize(
    ("name", "cap"), [("smoke", 18), ("smoke20", 24), ("smoke30", 36), ("smoke55", 64)]
)
def test_smoke_configs_load_in_place(name: str, cap: int) -> None:
    repo = Path(__file__).resolve().parents[1]
    cfg = load_pipeline_config(repo / "configs" / f"pipeline.{name}.yaml")
    assert cfg.run_root == repo / "runs" / name
    assert cfg.index.collection == name
    assert cfg.discovery.config.name == f"discovery.{name}.yaml"
    disc = yaml.safe_load(cfg.discovery.config.read_text(encoding="utf-8"))
    categories = yaml.safe_load(
        (cfg.discovery.config.parent / disc["categories_path"]).read_text(encoding="utf-8")
    )["categories"]
    assert disc["max_results"] * len(disc["sources"]) * len(categories) == cap


def test_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_pipeline_config(tmp_path / "nope.yaml")


def test_missing_required_key(project: Path) -> None:
    path = project / "pipeline.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    del data["screening"]
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(ConfigError, match="screening"):
        load_pipeline_config(path)


def test_unknown_key(project: Path) -> None:
    _edit(project / "pipeline.yaml", screening__typo=1)
    with pytest.raises(ConfigError, match="screening.typo"):
        load_pipeline_config(project / "pipeline.yaml")


def test_unknown_label(project: Path) -> None:
    _edit(project / "pipeline.yaml", index__include_labels=["HIGH", "MAYBE"])
    with pytest.raises(ConfigError, match="include_labels"):
        load_pipeline_config(project / "pipeline.yaml")


def test_missing_referenced_file(project: Path) -> None:
    (project / "configs" / "sanitize.yaml").unlink()
    with pytest.raises(ConfigError, match="privacy.sanitize_config"):
        load_pipeline_config(project / "pipeline.yaml")


def test_own_documents_sanitize_cannot_be_turned_off(project: Path) -> None:
    _edit(project / "pipeline.yaml", own_documents__sanitize=False)
    with pytest.raises(ConfigError, match="always sanitized"):
        load_pipeline_config(project / "pipeline.yaml")


def test_bad_run_name(project: Path) -> None:
    _edit(project / "pipeline.yaml", run_name="../escape")
    with pytest.raises(ConfigError, match="run_name"):
        load_pipeline_config(project / "pipeline.yaml")


def test_remote_db_uri_kept(project: Path) -> None:
    _edit(project / "pipeline.yaml", index__db_uri="http://127.0.0.1:19530")
    cfg = load_pipeline_config(project / "pipeline.yaml")
    assert cfg.index.db_uri == "http://127.0.0.1:19530"


@pytest.mark.parametrize(
    ("platform", "expected"),
    [("win32", "http://127.0.0.1:19530"), ("darwin", "file"), ("linux", "file")],
)
def test_db_uri_auto(
    project: Path, monkeypatch: pytest.MonkeyPatch, platform: str, expected: str
) -> None:
    from chitchat import config

    monkeypatch.setattr(config.sys, "platform", platform)
    _edit(project / "pipeline.yaml", index__db_uri="auto")
    cfg = load_pipeline_config(project / "pipeline.yaml")
    if expected == "file":
        assert cfg.index.db_uri == str(cfg.run_root / "milvus.db")
    else:
        assert cfg.index.db_uri == expected


def test_milvus_lite_uses_default_database() -> None:
    from chitchat.stages.index import milvus_db_name

    assert milvus_db_name("/runs/x/milvus.db", "review") == "default"
    assert milvus_db_name("http://127.0.0.1:19530", "review") == "review"
