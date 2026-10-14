"""Schema, LLM outcomes, store and the screener, with a fake chat model."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from chitchat.config import LLMSettings, ScreeningSettings
from chitchat.screening.criteria import load_criteria
from chitchat.screening.llm import StructuredCaller
from chitchat.screening.schema import extraction_model, screening_model
from chitchat.screening.store import ScreeningStore, redecide
from chitchat.stages.screen import Screener

REPO = Path(__file__).resolve().parents[1]
GOLDEN = Path(__file__).parent / "golden" / "screening_schema.json"
CRITERIA = load_criteria(REPO / "configs" / "criteria.example.yaml")


# --- Fakes -----------------------------------------------------------------------


def good_answers(**overrides: Any) -> dict[str, Any]:
    answers = {}
    for c in CRITERIA.criteria:
        value = "3" if c.type == "score" else "yes"
        answers[c.id] = {"answer": overrides.get(c.id, value), "evidence": f"quote for {c.id}"}
    answers["notes"] = ""
    return answers


def good_extraction() -> dict[str, Any]:
    return {
        "datasets": {"answer": ["Common Crawl"], "evidence": "We use Common Crawl."},
        "data_sources": {"answer": ["web"], "evidence": "web"},
        "languages": {"answer": None, "evidence": ""},
        "consent_approach": {"answer": "opt-out", "evidence": "opt-out"},
    }


class FakeStructured:
    def __init__(self, model: FakeChatModel, schema: type) -> None:
        self.model = model
        self.schema = schema

    def invoke(self, messages: list[Any]) -> dict[str, Any]:
        self.model.calls.append(self.schema.__name__)
        behavior = self.model.behavior(messages, self.schema)
        raw = SimpleNamespace(
            usage_metadata={"input_tokens": 10, "output_tokens": 5},
            additional_kwargs=behavior.get("kwargs", {}),
        )
        if "raise" in behavior:
            raise behavior["raise"]
        parsed = behavior.get("parsed")
        return {
            "raw": raw,
            "parsed": self.schema.model_validate(parsed) if parsed is not None else None,
            "parsing_error": behavior.get("parsing_error"),
        }


class FakeChatModel:
    """Answers per paper title. `behavior(messages, schema)` returns what to do."""

    def __init__(self, by_title: dict[str, dict[str, Any]] | None = None) -> None:
        self.by_title = by_title or {}
        self.calls: list[str] = []
        self.temperature = 0

    def with_structured_output(self, schema: type, include_raw: bool = False) -> FakeStructured:
        assert include_raw
        return FakeStructured(self, schema)

    def behavior(self, messages: list[Any], schema: type) -> dict[str, Any]:
        text = messages[-1].content
        for title, behavior in self.by_title.items():
            if f"TITLE: {title}\n" in text:
                if schema.__name__ == "ExtractedFields":
                    return {"parsed": good_extraction()}
                return behavior
        if schema.__name__ == "ExtractedFields":
            return {"parsed": good_extraction()}
        return {"parsed": good_answers()}


def settings(**overrides: Any) -> ScreeningSettings:
    base = {
        "criteria": REPO / "configs" / "criteria.example.yaml",
        "llm": LLMSettings(llm_name="gpt-4o-mini"),
        "min_year": 2020,
        "min_chars": 500,
    }
    return ScreeningSettings(**(base | overrides))


def paper(title: str, **overrides: Any) -> dict[str, Any]:
    return {
        "title": title,
        "doi": f"10.1/{title.lower().replace(' ', '-')}",
        "year": 2024,
        "abstract": "a" * 400,
        "extracted_text": "Full text. " * 100,
        "source": "openalex",
        "authors": ["[PERSON_1]"],
        "pdf_status": "downloaded",
        **overrides,
    }


def screener(model: FakeChatModel) -> Screener:
    return Screener(CRITERIA, settings(), model, "OPENAI", sanitized=True)


# --- Schema ------------------------------------------------------------------------


def test_screening_schema_matches_golden() -> None:
    schema = screening_model(CRITERIA).model_json_schema()
    if not GOLDEN.exists():  # first run writes it; review the file and commit it
        GOLDEN.parent.mkdir(exist_ok=True)
        GOLDEN.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
    assert schema == json.loads(GOLDEN.read_text(encoding="utf-8"))


def test_score_answers_are_strings() -> None:
    schema = screening_model(CRITERIA).model_json_schema()
    humanity = schema["$defs"]["HumanityAnswer"]["properties"]["answer"]
    assert humanity["enum"] == ["0", "1", "2", "3", "unclear"]


def test_extraction_answers_can_be_null() -> None:
    model = extraction_model(CRITERIA)
    parsed = model.model_validate(good_extraction())
    assert parsed.languages.answer is None


# --- LLM outcomes ------------------------------------------------------------------


class _Model:
    def __init__(self, result: dict[str, Any] | Exception) -> None:
        self.result = result
        self.temperature = 0

    def with_structured_output(self, schema, include_raw=False):
        return SimpleNamespace(invoke=self._invoke)

    def _invoke(self, messages):
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def _raw(**kwargs):
    return SimpleNamespace(
        usage_metadata={"input_tokens": 3, "output_tokens": 1}, additional_kwargs=kwargs
    )


def test_caller_ok() -> None:
    out = StructuredCaller(
        _Model({"raw": _raw(), "parsed": object(), "parsing_error": None}), dict
    )([])
    assert out.status == "ok" and out.usage == {"input_tokens": 3, "output_tokens": 1}


def test_caller_refused() -> None:
    result = {"raw": _raw(refusal="I can't help"), "parsed": None, "parsing_error": None}
    assert StructuredCaller(_Model(result), dict)([]).status == "refused"


def test_caller_invalid() -> None:
    result = {"raw": _raw(), "parsed": None, "parsing_error": ValueError("bad json " * 200)}
    out = StructuredCaller(_Model(result), dict)([])
    assert out.status == "invalid" and len(out.error) <= 500


def test_caller_error() -> None:
    out = StructuredCaller(_Model(RuntimeError("boom")), dict)([])
    assert out.status == "error" and "boom" in out.error


def test_bad_api_key_stops_the_run() -> None:
    from chitchat.screening.llm import FatalLLMError

    class AuthenticationError(Exception):
        pass

    with pytest.raises(FatalLLMError, match="API key"):
        StructuredCaller(_Model(AuthenticationError("401 sk-proj-***abcd")), dict)([])


def test_temperature_retry_once() -> None:
    class Picky(_Model):
        def _invoke(self, messages):
            if self.temperature is not None:
                raise ValueError("Unsupported parameter: 'temperature'")
            return {"raw": _raw(), "parsed": object(), "parsing_error": None}

    model = Picky({})
    caller = StructuredCaller(model, dict)
    assert caller([]).status == "ok"
    assert model.temperature is None


# --- Screener ----------------------------------------------------------------------


def test_screened_record_shape() -> None:
    model = FakeChatModel()
    record = screener(model).screen(paper("Good Paper"))
    assert record["status"] == "screened"
    assert record["paper_id"] == "doi:10.1/good-paper"
    assert record["decision"]["label"] == "EXCLUDE"  # disregards_consent == yes in good_answers
    assert record["answers"]["humanity"] == {"answer": 3, "evidence": "quote for humanity"}
    assert record["extracted"] is None  # no extraction for EXCLUDE
    assert record["metadata"]["source"] == "openalex"
    prov = record["provenance"]
    assert prov["criteria"] == "humanitarian-llm-data@1"
    assert prov["content"] == "full_text" and prov["sanitized"] is True
    assert prov["usage"] == {"input_tokens": 10, "output_tokens": 5}
    assert model.calls == ["ScreeningAnswers"]


def test_included_paper_gets_extraction() -> None:
    answers = good_answers(disregards_consent="no", discriminatory_or_military="no")
    model = FakeChatModel({"Kept": {"parsed": answers}})
    record = screener(model).screen(paper("Kept"))
    assert record["decision"]["label"] == "HIGH"
    assert record["extracted"]["datasets"]["answer"] == ["Common Crawl"]
    assert record["provenance"]["usage"] == {"input_tokens": 20, "output_tokens": 10}


def test_skips_before_any_call() -> None:
    model = FakeChatModel()
    s = screener(model)
    assert s.screen(paper("Old", year=2010))["skip_reason"] == "before_min_year"
    assert s.screen(paper("Empty", extracted_text=None, abstract=None))["skip_reason"] == "no_text"
    assert model.calls == []


@pytest.mark.parametrize(
    ("behavior", "status"),
    [
        ({"parsed": None, "kwargs": {"refusal": "no"}}, "refused"),
        ({"parsed": None, "parsing_error": ValueError("bad")}, "invalid"),
        ({"raise": RuntimeError("down")}, "error"),
    ],
)
def test_failures_do_not_stop_the_run(behavior, status, tmp_path: Path) -> None:
    model = FakeChatModel({"Bad": behavior})
    s = screener(model)
    store = ScreeningStore(tmp_path / "screening.jsonl")
    for p in (paper("Bad"), paper("Fine")):
        store.append(s.screen(p))
    statuses = {r["title"]: r["status"] for r in store.records()}
    assert statuses == {"Bad": status, "Fine": "screened"}


# --- Store ---------------------------------------------------------------------------


def test_resume_reuses_final_and_retries_failed(tmp_path: Path) -> None:
    store = ScreeningStore(tmp_path / "screening.jsonl")
    s = screener(FakeChatModel({"Bad": {"raise": RuntimeError("x")}}))
    for p in (paper("Good"), paper("Bad"), paper("Old", year=1999)):
        store.append(s.screen(p))
    done = store.done_ids(CRITERIA.hash, "gpt-4o-mini")
    assert done == {"doi:10.1/good", "doi:10.1/old"}
    assert store.done_ids(CRITERIA.hash, "other-model") == set()
    assert store.done_ids("sha256:other", "gpt-4o-mini") == set()


def test_redecide_changes_labels_without_llm_calls(tmp_path: Path) -> None:
    import dataclasses

    path = tmp_path / "screening.jsonl"
    store = ScreeningStore(path)
    model = FakeChatModel()
    store.append(screener(model).screen(paper("P")))
    assert store.records()[0]["decision"]["label"] == "EXCLUDE"
    calls_before = len(model.calls)

    # New rules: everything is LOW. Same hash, because rules are not hashed.
    lenient = dataclasses.replace(CRITERIA, rules=(CRITERIA.rules[-1],))
    assert redecide(path, lenient) == 1
    assert store.records()[0]["decision"]["label"] == "LOW"
    assert len(model.calls) == calls_before
