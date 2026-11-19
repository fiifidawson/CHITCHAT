"""Screening criteria drafted from the question: the file, its rules, and the conversation."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import yaml

from chitchat.config import load_pipeline_config
from chitchat.run_dir import RunDir
from chitchat.screening.criteria import load_criteria
from chitchat.screening.rules import decide
from chitchat.search.criteria_draft import (
    CriteriaDraft,
    criteria_file,
    draft_criteria,
    write_criteria,
)
from chitchat.search.plan import SearchPlan
from chitchat.search.session import write_run_config

DRAFT = {
    "context": "How humanitarian organisations obtain informed consent when collecting data.",
    "must": [{"id": "consent", "question": "Is the paper about informed consent for data?"}],
    "exclude": [{"id": "Animal-Studies", "question": "Is it only about animal research?"}],
    "stronger": [
        {"id": "humanitarian", "question": "Is it set in a humanitarian or crisis context?"},
        {"id": "empirical", "question": "Does it report real data or a case study?"},
    ],
    "extract": [
        {"id": "consent", "question": "How was consent obtained?"},  # same id as a must question
        {"id": "population", "question": "Who gave consent?"},
    ],
}
PLAN = SearchPlan(
    concepts=[], categories=[{"name": "Consent in crises", "words": []}], rationale=""
)


def _criteria(tmp_path: Path) -> Any:
    path = write_criteria(
        tmp_path / "criteria.yaml", criteria_file(CriteriaDraft(**DRAFT), "run-1", "q?")
    )
    return load_criteria(path)


def _label(criteria: Any, **answers: str) -> str:
    return decide(list(criteria.rules), answers)["label"]


def test_drafted_file_loads_with_valid_unique_ids(tmp_path: Path) -> None:
    criteria = _criteria(tmp_path)
    ids = [c.id for c in criteria.criteria] + [e.id for e in criteria.extract]
    assert ids == [
        "consent",
        "animal_studies",
        "humanitarian",
        "empirical",
        "consent_2",
        "population",
    ]
    assert criteria.ref == "run-1@1"
    assert "q?" in criteria.context  # the screening model sees the question


def test_drafted_rules(tmp_path: Path) -> None:
    c = _criteria(tmp_path)
    base = {"consent": "yes", "animal_studies": "no", "humanitarian": "no", "empirical": "no"}
    assert _label(c, **{**base, "consent": "no"}) == "EXCLUDE"
    assert _label(c, **{**base, "consent": "unclear"}) == "LOW"  # unclear is not a no
    assert _label(c, **{**base, "animal_studies": "yes"}) == "EXCLUDE"
    assert _label(c, **base) == "LOW"
    assert _label(c, **{**base, "empirical": "yes"}) == "MEDIUM"
    assert _label(c, **{**base, "empirical": "yes", "humanitarian": "yes"}) == "HIGH"


def test_run_config_points_at_the_drafted_criteria(project: Path) -> None:
    cfg = load_pipeline_config(project / "pipeline.yaml")
    run = RunDir(project / "runs" / "consent-run")
    criteria = write_criteria(run.criteria, criteria_file(CriteriaDraft(**DRAFT), "c", "q"))
    discovery = run.search / "discovery.yaml"
    discovery.write_text("sources: [openalex]\n", encoding="utf-8")
    path = write_run_config(project / "pipeline.yaml", cfg, run.root, discovery, "deep", criteria)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert data["screening"]["criteria"] == "search/criteria.yaml"
    assert data["privacy"]["mask"] is False  # the switch is written out, easy to find
    assert load_pipeline_config(path).screening.criteria == criteria.resolve()


class FakeDrafter:
    def __init__(self) -> None:
        self.calls: list[list[Any]] = []

    def criteria(self, messages: list[Any]) -> CriteriaDraft:
        self.calls.append(messages)
        return CriteriaDraft(**DRAFT)


class FakeIO:
    def __init__(self, choices: list[str], answers: list[str] | None = None) -> None:
        self.choices, self.answers = list(choices), list(answers or [])

    def show(self, renderable: Any) -> None:
        pass

    def ask(self, prompt: str) -> str:
        return self.answers.pop(0)

    def choose(self, prompt: str, choices: list[str], default: str) -> str:
        return self.choices.pop(0)


def test_change_then_accept_sends_the_answers_and_the_request() -> None:
    drafter = FakeDrafter()
    io = FakeIO(["c", "a"], ["drop the animal question"])
    clarified = [("Which setting?", "refugee camps"), ("Skipped?", "")]
    result = draft_criteria("consent?", clarified, PLAN, drafter, io)
    assert result is not None
    _, log = result
    first = drafter.calls[0][-1].content
    assert "refugee camps" in first and "Skipped?" not in first
    assert "Consent in crises" in first
    assert "drop the animal question" in drafter.calls[1][-1].content
    assert log["turns"][0]["feedback"] == "drop the animal question" and "accepted" in log


def test_quit_and_auto_accept() -> None:
    assert draft_criteria("q", [], PLAN, FakeDrafter(), FakeIO(["q"])) is None
    assert draft_criteria("q", [], PLAN, FakeDrafter(), FakeIO([]), auto_accept=True)


def test_drafter_parses_the_model_reply() -> None:
    from chitchat.search.drafting import Drafter

    class Model:
        def with_structured_output(self, schema: type, include_raw: bool = False) -> Any:
            def invoke(messages: list[Any]) -> dict[str, Any]:
                raw = SimpleNamespace(usage_metadata={}, additional_kwargs={})
                return {"raw": raw, "parsed": schema.model_validate(DRAFT), "parsing_error": None}

            return SimpleNamespace(invoke=invoke)

    assert Drafter(Model()).criteria([]).must[0].id == "consent"
