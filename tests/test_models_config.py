"""One model setting for every step, open-model snippets, and the model-server check."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pytest
import yaml

from chitchat.config import ConfigError, LLMSettings, load_pipeline_config
from chitchat.screening.llm import check_llm_reachable

REPO = Path(__file__).resolve().parents[1]
OLLAMA = "http://localhost:11434/v1"


def _write(project: Path, change: dict[str, Any]) -> Path:
    path = project / "pipeline.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    for key, value in change.items():
        section, _, field = key.partition(".")
        if field:
            data.setdefault(section, {})[field] = value
        else:
            data[section] = value
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def test_sections_inherit_top_level_llm(project: Path) -> None:
    cfg = load_pipeline_config(project / "pipeline.yaml")
    for llm in (cfg.screening_llm, cfg.ask_llm, cfg.search_llm, cfg.answer_llm, cfg.judge_llm):
        assert llm.llm_name == "qwen3.5:9b" and llm.base_url == OLLAMA


def test_a_section_override_wins(project: Path) -> None:
    path = _write(project, {"evaluate.judge_llm": {"llm_name": "gpt-oss:20b", "base_url": OLLAMA}})
    cfg = load_pipeline_config(path)
    assert cfg.judge_llm.llm_name == "gpt-oss:20b"
    assert cfg.answer_llm.llm_name == "qwen3.5:9b"


def test_a_model_is_required(project: Path) -> None:
    path = _write(project, {"llm": None})
    with pytest.raises(ConfigError, match="set a model under `llm:`"):
        load_pipeline_config(path)


def test_structured_output_is_not_sent_to_mmore() -> None:
    llm = LLMSettings(llm_name="m", base_url=OLLAMA, structured_output="json_mode")
    assert "structured_output" not in llm.to_mmore()


@pytest.mark.parametrize(
    "name", sorted(p.name for p in (REPO / "configs" / "models").glob("*.yaml"))
)
def test_model_snippets_parse(name: str) -> None:
    data = yaml.safe_load((REPO / "configs" / "models" / name).read_text(encoding="utf-8"))
    LLMSettings.model_validate(data["llm"])


def test_shipped_configs_use_an_open_local_model() -> None:
    paths = [
        *(REPO / "configs").glob("pipeline.*.yaml"),
        *(REPO / "examples").glob("*/pipeline.yaml"),
    ]
    assert paths
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "gpt-4o" not in text, path
        assert yaml.safe_load(text)["llm"]["base_url"] == OLLAMA, path


# --- check_llm_reachable ------------------------------------------------------------------


def _models(*names: str) -> httpx.Response:
    request = httpx.Request("GET", f"{OLLAMA}/models")
    return httpx.Response(200, json={"data": [{"id": n} for n in names]}, request=request)


def test_reachable_and_pulled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(httpx, "get", lambda url, **kw: _models("qwen3.5:9b"))
    check_llm_reachable(LLMSettings(llm_name="qwen3.5:9b", base_url=OLLAMA))


def test_model_not_pulled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(httpx, "get", lambda url, **kw: _models("gemma4:12b"))
    with pytest.raises(ConfigError, match="ollama pull qwen3.5:9b"):
        check_llm_reachable(LLMSettings(llm_name="qwen3.5:9b", base_url=OLLAMA))


def test_ollama_not_running(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(url: str, **kw: Any) -> httpx.Response:
        raise httpx.ConnectError("refused")

    monkeypatch.setattr(httpx, "get", refuse)
    with pytest.raises(ConfigError, match="Is Ollama running"):
        check_llm_reachable(LLMSettings(llm_name="qwen3.5:9b", base_url=OLLAMA))


def test_hosted_without_base_url_is_not_checked(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(url: str, **kw: Any) -> httpx.Response:
        raise AssertionError("should not be called")

    monkeypatch.setattr(httpx, "get", fail)
    check_llm_reachable(LLMSettings(llm_name="gpt-4o-mini"))


def test_json_mode_puts_the_schema_in_the_prompt() -> None:
    from types import SimpleNamespace

    from pydantic import BaseModel

    from chitchat.screening.llm import StructuredCaller

    class Answer(BaseModel):
        verdict: str

    seen: list[Any] = []

    class Model:
        def with_structured_output(self, schema: type, include_raw: bool, method: str) -> Any:
            assert method == "json_mode"

            def invoke(messages: list[Any]) -> dict[str, Any]:
                seen.extend(messages)
                raw = SimpleNamespace(usage_metadata={}, additional_kwargs={})
                return {"raw": raw, "parsed": Answer(verdict="ok"), "parsing_error": None}

            return SimpleNamespace(invoke=invoke)

    result = StructuredCaller(Model(), Answer, "json_mode")(["question"])
    assert result.status == "ok"
    assert '"verdict"' in seen[-1].content
