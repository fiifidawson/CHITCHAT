"""The planning conversation, with a fake LLM and scripted answers. No network."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from chitchat.config import DEFAULT_PRESETS, SearchPreset
from chitchat.jsonl import read_json
from chitchat.run_dir import RunDir
from chitchat.search.drafting import Drafter
from chitchat.search.session import plan_search, save_plan
from chitchat.stages import StageError

DEEP = SearchPreset(**DEFAULT_PRESETS["deep"])
SHALLOW = SearchPreset(**DEFAULT_PRESETS["shallow"])

QUESTIONS = {
    "questions": [
        {"question": "Which setting?", "suggestions": ["crisis response", "health"]},
        {"question": "Which years?", "suggestions": ["since 2020", "any"]},
    ]
}


def _plan(extra: str = "") -> dict[str, Any]:
    return {
        "concepts": [
            {"word": "consent", "synonyms": ["informed consent", "opt-out"]},
            {"word": f"training data{extra}", "synonyms": ["datasets"]},
            {"word": "humanitarian", "synonyms": ["crisis response"]},
        ],
        "categories": [
            {"name": "Consent in data", "words": ["consent", f"training data{extra}"]},
            {"name": "Humanitarian data", "words": ["humanitarian", f"training data{extra}"]},
            {"name": "Humanitarian consent", "words": ["humanitarian", "consent"]},
        ],
        "rationale": "Covers consent, data and humanitarian settings.",
    }


class FakeChatModel:
    """Returns scripted answers per schema and records every call's messages."""

    def __init__(self, plans: list[dict[str, Any]], questions: dict[str, Any] | None = None):
        self.plans = list(plans)
        self.questions = questions or QUESTIONS
        self.calls: list[tuple[str, list[Any]]] = []

    def with_structured_output(self, schema: type, include_raw: bool = False) -> Any:
        def invoke(messages: list[Any]) -> dict[str, Any]:
            self.calls.append((schema.__name__, messages))
            data = self.questions if schema.__name__ == "ClarifyingQuestions" else self.plans.pop(0)
            raw = SimpleNamespace(usage_metadata={}, additional_kwargs={})
            return {"raw": raw, "parsed": schema.model_validate(data), "parsing_error": None}

        return SimpleNamespace(invoke=invoke)

    def kinds(self) -> list[str]:
        return [name for name, _ in self.calls]


class FakeIO:
    def __init__(self, answers: list[str] | None = None, choices: list[str] | None = None):
        self.answers = list(answers or [])
        self.choices = list(choices or [])
        self.shown: list[Any] = []

    def show(self, renderable: Any) -> None:
        self.shown.append(renderable)

    def ask(self, prompt: str) -> str:
        return self.answers.pop(0)

    def choose(self, prompt: str, choices: list[str], default: str) -> str:
        return self.choices.pop(0)

    def text(self) -> str:
        return " ".join(str(getattr(r, "plain", r)) for r in self.shown)


def _content(messages: list[Any]) -> str:
    return "\n".join(m.content for m in messages)


def test_shallow_asks_nothing_and_accepts() -> None:
    model = FakeChatModel([_plan()])
    result = plan_search(
        "consent in LLM data", "shallow", SHALLOW, Drafter(model), FakeIO(choices=["a"])
    )
    assert result is not None
    assert model.kinds() == ["SearchPlan"]
    assert len(result.plan.categories) <= SHALLOW.max_categories
    assert len(result.queries) == len(result.plan.categories)


def test_deep_asks_clarifying_questions_first() -> None:
    model = FakeChatModel([_plan()])
    io = FakeIO(answers=["1", "only peer-reviewed work"], choices=["a"])
    result = plan_search("consent in LLM data", "deep", DEEP, Drafter(model), io)
    assert model.kinds() == ["ClarifyingQuestions", "SearchPlan"]
    sent = _content(model.calls[1][1])
    assert "Which setting? crisis response" in sent  # "1" picks the first suggestion
    assert "Which years? only peer-reviewed work" in sent
    assert result is not None and len(result.plan.categories) == 3
    assert [c["answer"] for c in result.log["clarifying"]] == [
        "crisis response",
        "only peer-reviewed work",
    ]


def test_change_then_accept_sends_the_history() -> None:
    model = FakeChatModel([_plan(), _plan(extra=" v2")])
    io = FakeIO(answers=["", "", "add refugee camps"], choices=["c", "a"])
    result = plan_search("consent in LLM data", "deep", DEEP, Drafter(model), io)
    assert model.kinds() == ["ClarifyingQuestions", "SearchPlan", "SearchPlan"]
    revision = model.calls[2][1]
    assert "Change request: add refugee camps" in revision[-1].content
    assert '"training data"' in revision[-2].content  # the previous draft, as the user saw it
    assert result is not None
    assert any(c.word == "training data v2" for c in result.plan.concepts)
    assert result.log["turns"][0]["feedback"] == "add refugee camps"


def test_empty_feedback_asks_again_without_redrafting() -> None:
    model = FakeChatModel([_plan()])
    io = FakeIO(answers=[""], choices=["c", "a"])
    result = plan_search("q", "shallow", SHALLOW, Drafter(model), io)
    assert result is not None and model.kinds() == ["SearchPlan"]


def test_quit_returns_nothing() -> None:
    model = FakeChatModel([_plan()])
    assert plan_search("q", "shallow", SHALLOW, Drafter(model), FakeIO(choices=["q"])) is None


def test_auto_accept_skips_questions() -> None:
    model = FakeChatModel([_plan()])
    result = plan_search("q", "deep", DEEP, Drafter(model), FakeIO(), auto_accept=True)
    assert result is not None and model.kinds() == ["SearchPlan"]


def test_question_is_masked_before_sending() -> None:
    model = FakeChatModel([_plan()])
    io = FakeIO(choices=["a"])
    result = plan_search(
        "Sarah Mensah asks about consent",
        "shallow",
        SHALLOW,
        Drafter(model),
        io,
        mask=lambda text: text.replace("Sarah Mensah", "[PERSON_1]"),
    )
    sent = _content(model.calls[0][1])
    assert "Sarah" not in sent and "[PERSON_1] asks about consent" in sent
    assert "masked before sending" in io.text()
    assert result is not None and result.log["question_sent"] == "[PERSON_1] asks about consent"


def test_failed_draft_is_a_clear_error() -> None:
    class Broken(FakeChatModel):
        def with_structured_output(self, schema: type, include_raw: bool = False) -> Any:
            raw = SimpleNamespace(usage_metadata={}, additional_kwargs={})
            out = {"raw": raw, "parsed": None, "parsing_error": ValueError("bad json")}
            return SimpleNamespace(invoke=lambda messages: out)

    with pytest.raises(StageError, match="Couldn't draft the search"):
        plan_search("q", "shallow", SHALLOW, Drafter(Broken([])), FakeIO(choices=["a"]))


def test_save_plan_writes_files_and_conversation(tmp_path: Path) -> None:
    model = FakeChatModel([_plan()])
    result = plan_search("consent", "shallow", SHALLOW, Drafter(model), FakeIO(choices=["a"]))
    assert result is not None
    run = RunDir(tmp_path)
    discovery = save_plan(run, result, SHALLOW)
    assert discovery == run.search / "discovery.yaml"
    assert (run.search / "synonyms.jsonl").exists() and (run.search / "categories.yaml").exists()
    log = read_json(run.plan)
    assert log["question"] == "consent" and log["accepted"] and log["saved"]


def test_rule_breaking_draft_is_repaired_before_showing() -> None:
    bad = {
        "concepts": [{"word": "consent", "synonyms": ["informed consent"]}],
        "categories": [{"name": "One concept", "words": ["consent", "informed consent"]}],
        "rationale": "",
    }
    model = FakeChatModel([bad, _plan()])
    io = FakeIO(choices=["a"])
    result = plan_search("q", "shallow", SHALLOW, Drafter(model), io)
    assert model.kinds() == ["SearchPlan", "SearchPlan"]
    repair = model.calls[1][1][-1].content
    assert "breaks the rules" in repair and "fewer than 2" in repair
    assert result is not None and len(result.plan.categories[0].words) == 2
