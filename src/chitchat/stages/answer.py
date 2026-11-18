"""Stage 7: answer the run's question with a decision brief.

The question is the one the search was planned from (masked, with the clarifying answers),
or `answer.question` from the config. Without either, the stage is skipped.
"""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from chitchat.config import PipelineConfig
from chitchat.jsonl import append_jsonl, read_json, write_json
from chitchat.run_dir import RunDir
from chitchat.stages import StageError

log = logging.getLogger(__name__)

OVERVIEW_TITLES = 15


@dataclass
class RunQuestion:
    text: str  # masked
    clarifications: list[tuple[str, str]] = field(default_factory=list)
    origin: str = "search plan"


def has_question(cfg: PipelineConfig, run: RunDir) -> bool:
    """Whether there is a question to answer. Cheap: masks nothing."""
    if run.plan.exists() and (read_json(run.plan).get("question_sent") or "").strip():
        return True
    return bool(cfg.answer.question and cfg.answer.question.strip())


def run_question(cfg: PipelineConfig, run: RunDir) -> RunQuestion | None:
    """The question to answer: the search plan's, else the config's, else None."""
    if run.plan.exists():
        plan = read_json(run.plan)
        sent = (plan.get("question_sent") or "").strip()
        if sent:
            clarifications = [
                (c["question"], c.get("answer") or "") for c in plan.get("clarifying") or []
            ]
            return RunQuestion(sent, clarifications, "search plan")
    if cfg.answer.question and cfg.answer.question.strip():
        from chitchat.search.session import question_masker

        masked = question_masker(cfg.privacy.rag_privacy_config)(cfg.answer.question.strip())
        return RunQuestion(masked, [], "config")
    return None


def corpus_overview(sources: dict[str, dict[str, Any]]) -> str:
    """Counts per label and the titles of the most relevant papers, for the Planner."""
    papers = [s for s in sources.values() if s.get("kind") == "paper"]
    docs = [s for s in sources.values() if s.get("kind") == "own_document"]
    labels = Counter(s.get("label") or "not screened" for s in papers)
    lines = [f"{len(papers)} papers ({', '.join(f'{k} {v}' for k, v in labels.items()) or 'none'})"]
    lines.append(f"{len(docs)} of the researcher's own documents")
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    ranked = sorted(papers, key=lambda s: order.get(s.get("label") or "", 3))
    titles = [s["title"] for s in ranked if s.get("title")][:OVERVIEW_TITLES]
    if titles:
        lines.append("Most relevant paper titles:")
        lines += [f"- {t}" for t in titles]
    return "\n".join(lines)


def run_answer(
    cfg: PipelineConfig,
    run: RunDir,
    chat_model: Any = None,
    search: Any = None,
) -> dict[str, Any] | None:
    """Write answer/brief.json, brief.md, evidence.json and trace.jsonl. None if skipped.

    `chat_model` and `search` are for tests; by default they come from the config.
    """
    from chitchat import ui
    from chitchat.agents.loop import Agents, LoopSettings, answer_question
    from chitchat.agents.render import brief_markdown, brief_view, build_brief

    if not has_question(cfg, run):
        ui.note(
            "No question to answer: this run has no search plan and no `answer.question`. Skipped."
        )
        return None
    if not run.sources.exists():
        raise StageError(f"Missing {run.sources}. Run export and index first.")
    sources = read_json(run.sources)

    from chitchat.screening.llm import FatalLLMError, build_chat_model

    llm = cfg.answer_llm
    provider = ""
    if chat_model is None:
        chat_model, provider = build_chat_model(llm)  # checks the model server first
    question = run_question(cfg, run)
    assert question is not None
    if search is None:
        from chitchat.agents.retrieval import milvus_search

        search = milvus_search(cfg, cfg.answer.k_per_query)

    run.answer.mkdir(parents=True, exist_ok=True)
    run.trace.unlink(missing_ok=True)

    def trace(event: dict[str, Any]) -> None:
        append_jsonl(run.trace, event)
        if event["role"] in ("planner", "writer", "critic", "retriever"):
            ui.note(_progress_line(event))

    ui.note(f"Question ({question.origin}): {question.text}")
    settings = LoopSettings(
        cfg.answer.max_rounds, cfg.answer.k_per_query, cfg.answer.max_evidence_chars
    )
    try:
        result = answer_question(
            question.text,
            question.clarifications,
            corpus_overview(sources),
            Agents(chat_model, llm.structured_output),
            search,
            settings,
            trace,
        )
    except FatalLLMError as e:
        from chitchat.stages.screen import _key_hint

        raise StageError(f"{e}{_key_hint(provider)}") from None

    brief = build_brief(question.text, result, llm.llm_name)
    write_json(run.brief_json, brief)
    write_json(run.evidence, result.evidence.to_json())
    run.brief_md.write_text(brief_markdown(brief, sources), encoding="utf-8")

    ui.console.print()
    ui.console.print(brief_view(brief, sources))
    ui.console.print()
    ui.print_box(
        "Answer",
        [
            ("Rounds", brief["rounds"], brief["stopped_because"]),
            ("Evidence", brief["evidence_passages"], "passages"),
            ("Model", "", llm.llm_name),
        ],
        footer=[f"Brief: {ui.shorten_path(run.brief_md)}", f"Steps: {ui.shorten_path(run.trace)}"],
    )
    return brief


def _progress_line(event: dict[str, Any]) -> str:
    role = event["role"].capitalize()
    where = f"round {event['round']}" if event["round"] else "start"
    if event["role"] == "retriever":
        return (
            f"  {role} ({where}): {len(event['queries'])} searches, "
            f"{event['new_passages']} new passages ({event['total_passages']} in all)"
        )
    status = "done" if event["status"] == "ok" else f"failed ({event['status']})"
    extra = ""
    output = event.get("output") or {}
    if event["role"] == "critic" and output:
        total = sum(output["scores"].values())
        extra = f": {output['verdict']}, score {total}/{2 * len(output['scores'])}"
    return f"  {role} ({where}) {status} in {event['seconds']:.0f}s{extra}"
