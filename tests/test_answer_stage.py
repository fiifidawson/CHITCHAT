"""The answer stage: which question it answers and what it writes."""

from __future__ import annotations

from pathlib import Path

import yaml
from agent_fakes import INDEX, PLAN, FakeIndex, ScriptedModel, _critique, _draft

from chitchat.config import load_pipeline_config
from chitchat.jsonl import read_json, read_jsonl, write_json
from chitchat.run_dir import RunDir
from chitchat.stages.answer import corpus_overview, run_answer, run_question
from chitchat.status import stage_details

SOURCES = {
    "P0001": {"kind": "paper", "title": "Chatbots at intake", "year": 2024, "label": "HIGH"},
    "P0002": {"kind": "paper", "title": "Privacy leaks", "year": 2023, "label": "LOW"},
    "D0001": {"kind": "own_document", "title": "notes.docx", "label": None},
}


def _config(project: Path, question: str | None = None):
    path = project / "pipeline.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["privacy"]["rag_privacy_config"] = None  # no Presidio in these tests
    data["answer"] = {"question": question} if question else {}
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return load_pipeline_config(path)


def _model() -> ScriptedModel:
    return ScriptedModel(Plan=[PLAN], BriefDraft=[_draft()], Critique=[_critique("accept", 2)])


def test_question_from_search_plan_wins(project: Path) -> None:
    cfg = _config(project, question="from the config")
    run = RunDir(cfg.run_root)
    write_json(
        run.plan,
        {
            "question": "Can [raw] Ana's team use chatbots?",
            "question_sent": "Can [PERSON_1]'s team use chatbots?",
            "clarifying": [{"question": "Which setting?", "suggestions": [], "answer": "camps"}],
        },
    )
    q = run_question(cfg, run)
    assert q is not None
    assert q.text == "Can [PERSON_1]'s team use chatbots?"  # the masked one, never the raw one
    assert q.clarifications == [("Which setting?", "camps")]
    assert q.origin == "search plan"


def test_question_from_config(project: Path) -> None:
    cfg = _config(project, question="Should we use chatbots?")
    q = run_question(cfg, RunDir(cfg.run_root))
    assert q is not None and q.text == "Should we use chatbots?" and q.origin == "config"


def test_no_question_skips(project: Path) -> None:
    cfg = _config(project)
    run = RunDir(cfg.run_root)
    assert run_answer(cfg, run, chat_model=_model(), search=FakeIndex(INDEX)) is None
    assert not run.brief_json.exists()


def test_writes_brief_files(project: Path) -> None:
    cfg = _config(project, question="Should we use chatbots for intake?")
    run = RunDir(cfg.run_root)
    write_json(run.sources, SOURCES)
    brief = run_answer(cfg, run, chat_model=_model(), search=FakeIndex(INDEX))
    assert brief is not None
    assert read_json(run.brief_json)["question"] == "Should we use chatbots for intake?"
    assert "## Bottom line" in run.brief_md.read_text(encoding="utf-8")
    assert {e["tag"] for e in read_json(run.evidence)} >= {"P0001"}
    roles = [e["role"] for e in read_jsonl(run.trace)]
    assert roles == ["planner", "retriever", "writer", "checks", "critic"]
    assert stage_details(run)["answer"] == "brief, 1 round, accepted by the Critic"


def test_overview_lists_relevant_titles_first() -> None:
    text = corpus_overview(SOURCES)
    assert "2 papers (HIGH 1, LOW 1)" in text
    assert "1 of the researcher's own documents" in text
    assert text.index("Chatbots at intake") < text.index("Privacy leaks")
    assert "notes.docx" not in text  # document file names stay out of prompts
