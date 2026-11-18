"""The answer loop with a scripted chat model and a fake index. No network."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from agent_fakes import INDEX, PLAN, FakeIndex, ScriptedModel, _critique, _draft

from chitchat.agents.checks import check_brief, cited_tags
from chitchat.agents.loop import Agents, LoopSettings, answer_question
from chitchat.agents.render import brief_markdown, brief_view, build_brief
from chitchat.agents.retrieval import Evidence
from chitchat.agents.schemas import BriefDraft, Critique
from chitchat.stages import StageError


def _run(model: ScriptedModel, index: FakeIndex | None = None, **settings: Any):
    events: list[dict[str, Any]] = []
    result = answer_question(
        "Should we use chatbots for intake?",
        [("Which setting?", "refugee camps")],
        "3 papers",
        Agents(model),
        index or FakeIndex(INDEX),
        LoopSettings(**settings),
        events.append,
    )
    return result, events


def test_accept_on_first_round() -> None:
    model = ScriptedModel(Plan=[PLAN], BriefDraft=[_draft()], Critique=[_critique("accept", 2)])
    result, events = _run(model)
    assert model.kinds() == ["Plan", "BriefDraft", "Critique"]
    assert result.stopped_because == "accepted by the Critic"
    assert result.best is not None and result.best.number == 1
    assert [e["role"] for e in events] == ["planner", "retriever", "writer", "checks", "critic"]
    # The clarification reaches the Planner and the Writer.
    assert "refugee camps" in model.prompt(0)
    assert "refugee camps" in model.prompt(1)


def test_revise_then_accept_uses_follow_ups_and_critique() -> None:
    index = FakeIndex(INDEX)
    model = ScriptedModel(
        Plan=[PLAN],
        BriefDraft=[_draft(), _draft()],
        Critique=[_critique("revise", 1, ["caseworkers trust"]), _critique("accept", 2)],
    )
    result, _ = _run(model, index)
    assert "caseworkers trust" in index.queries
    assert "D0001" in result.evidence.tags()  # found by the follow-up search
    rewrite = model.prompt(3)
    assert "Thin on harms." in rewrite and "Your previous brief" in rewrite
    assert result.stopped_because == "accepted by the Critic"
    assert len(result.rounds) == 2


def test_stops_at_round_limit() -> None:
    model = ScriptedModel(
        Plan=[PLAN],
        BriefDraft=[_draft(), _draft()],
        Critique=[_critique("revise", 0, ["caseworkers trust"]), _critique("revise", 1)],
    )
    result, _ = _run(model, max_rounds=2)
    assert result.stopped_because == "reached the round limit (2)"
    assert len(result.rounds) == 2


def test_stops_without_new_evidence_or_better_score() -> None:
    model = ScriptedModel(
        Plan=[PLAN],
        BriefDraft=[_draft(), _draft()],
        Critique=[_critique("revise", 1, ["nothing matches"]), _critique("revise", 1)],
    )
    result, _ = _run(model, max_rounds=5)
    assert result.stopped_because == "no new evidence and no better score"
    assert len(result.rounds) == 2


def test_unknown_citation_forces_a_rewrite() -> None:
    model = ScriptedModel(
        Plan=[PLAN],
        BriefDraft=[_draft("P0999"), _draft("P0001")],
        Critique=[_critique("accept", 2), _critique("accept", 2)],
    )
    result, _ = _run(model)
    assert len(result.rounds) == 2  # the Critic accepted, but the citation was invalid
    assert "P0999" in model.prompt(3)  # the failed check reaches the Writer
    assert result.best is not None and not result.best.checks.blocking


def test_planner_failure_is_a_stage_error() -> None:
    model = ScriptedModel(Plan=[None])
    with pytest.raises(StageError, match="Planner"):
        _run(model)


def test_writer_failure_keeps_previous_draft() -> None:
    model = ScriptedModel(
        Plan=[PLAN],
        BriefDraft=[_draft(), None],
        Critique=[_critique("revise", 1, ["caseworkers trust"])],
    )
    result, _ = _run(model)
    assert result.stopped_because.startswith("the Writer failed")
    assert result.best is not None and result.best.number == 1


def test_critic_scores_are_clamped() -> None:
    critique = Critique.model_validate(_critique("accept", 5))
    assert critique.scores.total() == 12


# --- Checks and evidence --------------------------------------------------------------------


def test_checks_find_unknown_and_unsourced() -> None:
    draft = BriefDraft.model_validate(_draft("P0009"))
    draft.options[0].benefits[0].sources = []
    result = check_brief(draft, {"P0001"})
    assert result.unknown_tags == ["P0009"]
    assert result.blocking
    text = " ".join(result.problems)
    assert "marked as evidence but has no source" in text
    assert "has no sourced benefit or risk" in text


def test_checks_pass_a_clean_draft() -> None:
    result = check_brief(BriefDraft.model_validate(_draft()), {"P0001"})
    assert result.problems == []


def test_cited_tags_include_inline_tags() -> None:
    data = _draft()
    data["bottom_line"] = "See [D0003]."
    assert cited_tags(BriefDraft.model_validate(data))[:2] == ["D0003", "P0001"]


def test_evidence_dedupes_and_caps() -> None:
    evidence = Evidence(max_chars=60)
    doc = {"page_content": "[P0001] " + "a" * 30, "metadata": {"id": 1, "file_path": "P0001"}}
    big = {"page_content": "b" * 100, "metadata": {"id": 2, "file_path": "P0002"}}
    assert evidence.add([doc, doc], "q") == 1
    assert evidence.add([big], "q") == 0
    assert evidence.dropped == 1
    assert evidence.tags() == {"P0001"}
    assert evidence.render().startswith("[P0001] ")


def test_evidence_reads_langchain_documents() -> None:
    doc = SimpleNamespace(page_content="text", metadata={"id": "x", "file_path": "D0001"})
    evidence = Evidence(max_chars=1000)
    evidence.add([doc], "q")
    assert evidence.render() == "[D0001] text"


# --- Rendering ------------------------------------------------------------------------------

SOURCES = {"P0001": {"title": "Chatbots at intake", "year": 2024, "doi": "10.1/x", "label": "HIGH"}}


def _brief() -> dict[str, Any]:
    model = ScriptedModel(Plan=[PLAN], BriefDraft=[_draft()], Critique=[_critique("accept", 2)])
    result, _ = _run(model)
    return build_brief("Should we use chatbots for intake?", result, "qwen3.5:9b")


def test_brief_records_the_loop() -> None:
    brief = _brief()
    assert brief["rounds"] == 1 and brief["verdict"] == "accept"
    assert brief["model"] == "qwen3.5:9b"
    assert "not the decision" in brief["caveat"]


def test_brief_markdown_has_sections_and_sources() -> None:
    md = brief_markdown(_brief(), SOURCES)
    for heading in ("## Bottom line", "## Options", "## Trade-offs", "## If this matters most"):
        assert heading in md
    assert "Evidence strength: **moderate**" in md
    assert "| accuracy | Good on simple cases [P0001] | Best |" in md
    assert "different settings or populations" in md
    assert "- [P0001] Chatbots at intake (2024) https://doi.org/10.1/x" in md


def test_brief_view_renders() -> None:
    from rich.console import Console

    console = Console(record=True, width=120)
    console.print(brief_view(_brief(), SOURCES))
    text = console.export_text()
    assert "Decision brief" in text and "evidence moderate" in text and "[P0001]" in text
