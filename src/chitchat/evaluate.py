"""`chitchat evaluate`: compare the answer loop with a baseline and with other systems.

For each question:
- baseline: one search (k = evaluate.baseline_k) and one Writer call with the same prompt,
  so the comparison isolates the loop (AMMORE's design);
- chitchat: the full loop;
- imported answers from other systems, if given: `<n>.md` (or .txt) per question, from 1.

A judge model compares chitchat with each other system, blind and in random order,
and scores both 1–5 on six metrics.
"""

from __future__ import annotations

import random
import re
from collections import defaultdict
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, BeforeValidator, Field

from chitchat.screening.llm import StructuredCaller
from chitchat.stages import StageError

OURS = "chitchat"
METRICS = (
    "coverage",
    "groundedness",
    "specificity",
    "tradeoffs",
    "humanitarian_awareness",
    "usefulness",
)


def _clamp(value: object) -> object:
    try:
        return min(5, max(1, int(value)))  # type: ignore[call-overload]
    except (TypeError, ValueError):
        return value


Score = Annotated[int, BeforeValidator(_clamp)]


class SideScores(BaseModel):
    """1 = poor, 5 = excellent."""

    coverage: Score = Field(description="Covers the question's parts and the options.")
    groundedness: Score = Field(description="Claims are tied to cited sources.")
    specificity: Score = Field(description="Concrete settings, numbers and harms.")
    tradeoffs: Score = Field(description="Options, criteria, conflicts and conditions.")
    humanitarian_awareness: Score = Field(description="Do no harm, impartiality, rights.")
    usefulness: Score = Field(description="Helps someone make the decision.")


class Judgement(BaseModel):
    a: SideScores
    b: SideScores
    winner: Literal["A", "B", "tie"]
    reason: str = Field(description="One or two sentences.")


JUDGE_SYSTEM = """You compare two answers to a question from a humanitarian researcher
who must make a decision. Judge only what is written. Do not prefer an answer for its length
or its style. Score each answer 1 (poor) to 5 (excellent) on:
- coverage: the question's parts and the realistic options;
- groundedness: claims are tied to cited sources, and guesses are labelled;
- specificity: concrete settings, populations, numbers and harms;
- tradeoffs: options compared on clear criteria, with conflicts and conditions;
- humanitarian_awareness: humanity, impartiality, neutrality, independence, do no harm,
  and the rights of affected people;
- usefulness: how much it helps someone decide.
Then pick the winner (A, B or tie) and say why in one or two sentences.
"""


def parse_questions(path: Path) -> list[str]:
    """One question per line. Blank lines and lines starting with # are skipped."""
    lines = path.read_text(encoding="utf-8").splitlines()
    questions = [
        line.strip() for line in lines if line.strip() and not line.strip().startswith("#")
    ]
    if not questions:
        raise StageError(f"No questions in {path}.")
    return questions


def parse_import(spec: str) -> tuple[str, Path]:
    """`name=folder` → (name, folder)."""
    name, sep, folder = spec.partition("=")
    name = name.strip()
    if not sep or not re.fullmatch(r"[A-Za-z0-9_-]+", name) or not folder.strip():
        raise StageError(f"--import needs name=folder, e.g. deepresearch=answers/; got {spec!r}.")
    if name in (OURS, "baseline"):
        raise StageError(f"--import name {name!r} is taken; pick another.")
    path = Path(folder.strip())
    if not path.is_dir():
        raise StageError(f"--import {name}: {path} is not a folder.")
    return name, path


def imported_answer(folder: Path, number: int) -> str | None:
    """Answer to question `number` (from 1): <number>.md or <number>.txt."""
    for suffix in (".md", ".txt"):
        path = folder / f"{number}{suffix}"
        if path.exists():
            return path.read_text(encoding="utf-8").strip() or None
    return None


# (question number from 1, masked question) -> answer text, or None if the system has none.
System = Callable[[int, str], str | None]


def _judge_messages(question: str, a: str, b: str) -> list[Any]:
    from langchain_core.messages import HumanMessage, SystemMessage

    user = f"Question: {question}\n\n=== Answer A ===\n{a}\n\n=== Answer B ===\n{b}"
    return [SystemMessage(content=JUDGE_SYSTEM), HumanMessage(content=user)]


def judge_pair(
    judge: StructuredCaller,
    question: str,
    ours: str,
    theirs: str,
    other: str,
    rng: random.Random,
) -> dict[str, Any]:
    """Blind comparison in random order, then unblinded to system names."""
    swapped = rng.random() < 0.5
    a, b = (theirs, ours) if swapped else (ours, theirs)
    names = {"A": other if swapped else OURS, "B": OURS if swapped else other}
    result = judge(_judge_messages(question, a, b))
    if result.status != "ok":
        return {"other": other, "status": result.status, "error": result.error}
    j = result.parsed
    assert isinstance(j, Judgement)
    return {
        "other": other,
        "status": "ok",
        "order": [names["A"], names["B"]],
        "scores": {names["A"]: j.a.model_dump(), names["B"]: j.b.model_dump()},
        "winner": "tie" if j.winner == "tie" else names[j.winner],
        "reason": j.reason,
    }


def run_evaluation(
    questions: list[str],
    systems: dict[str, System],
    judge: StructuredCaller,
    seed: int = 0,
    on_progress: Callable[[str], None] = lambda text: None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Returns (answers, judgements). `systems` must include OURS."""
    rng = random.Random(seed)
    answers: list[dict[str, Any]] = []
    judgements: list[dict[str, Any]] = []
    for number, question in enumerate(questions, 1):
        texts: dict[str, str | None] = {}
        for name, system in systems.items():
            on_progress(f"Question {number}/{len(questions)}: {name}")
            texts[name] = system(number, question)
            answers.append(
                {"question_no": number, "question": question, "system": name, "answer": texts[name]}
            )
        ours = texts.get(OURS)
        if not ours:
            continue
        for other, theirs in texts.items():
            if other == OURS or not theirs:
                continue
            on_progress(f"Question {number}/{len(questions)}: judging {OURS} vs {other}")
            judged = judge_pair(judge, question, ours, theirs, other, rng)
            judgements.append({"question_no": number, "question": question, **judged})
    return answers, judgements


def summarize(judgements: list[dict[str, Any]], settings: dict[str, Any]) -> str:
    """summary.md: means per metric, deltas, and win / tie / loss for chitchat."""
    by_other: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for j in judgements:
        by_other[j["other"]].append(j)
    lines = ["# Evaluation", ""]
    lines += [f"- {k}: {v}" for k, v in settings.items()]
    lines.append("")
    for other, items in by_other.items():
        ok = [j for j in items if j["status"] == "ok"]
        failed = len(items) - len(ok)
        lines += [f"## {OURS} vs {other}", ""]
        if not ok:
            lines += [f"No judgements ({failed} failed).", ""]
            continue
        wins = sum(j["winner"] == OURS for j in ok)
        ties = sum(j["winner"] == "tie" for j in ok)
        losses = len(ok) - wins - ties
        lines.append(f"{len(ok)} questions judged: {wins} wins, {ties} ties, {losses} losses.")
        if failed:
            lines.append(f"{failed} judgements failed and are left out.")
        lines += ["", f"| Metric | {OURS} | {other} | Delta |", "|---|---|---|---|"]
        for metric in METRICS:
            ours = sum(j["scores"][OURS][metric] for j in ok) / len(ok)
            theirs = sum(j["scores"][other][metric] for j in ok) / len(ok)
            lines.append(f"| {metric} | {ours:.2f} | {theirs:.2f} | {ours - theirs:+.2f} |")
        lines.append("")
    if not by_other:
        lines += ["Nothing was judged.", ""]
    lines.append(
        "Scores are 1–5 from one judge model, blind and in random order. "
        "A judge from another model family limits self-preference."
    )
    return "\n".join(lines) + "\n"


def run_id() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def pipeline_systems(
    agents: Any,
    search: Any,
    sources: dict[str, dict[str, Any]],
    overview: str,
    loop_settings: Any,
    baseline_k: int,
    model: str,
) -> dict[str, System]:
    """The baseline (one search, one Writer call) and the full loop, as answer texts."""
    from chitchat.agents.checks import check_brief
    from chitchat.agents.loop import answer_question
    from chitchat.agents.prompts import writer_messages
    from chitchat.agents.render import brief_markdown, build_brief
    from chitchat.agents.retrieval import Evidence
    from chitchat.agents.schemas import CAVEAT, Plan

    def baseline(_: int, question: str) -> str | None:
        evidence = Evidence(loop_settings.max_evidence_chars)
        evidence.add(search(question, baseline_k), question)
        plan = Plan(decision=question, options=[], criteria=[], sub_questions=[])
        result = agents.writer(writer_messages(question, [], plan, evidence.render()))
        if result.status != "ok":
            return None
        brief = {
            "question": question,
            **result.parsed.model_dump(),
            "caveat": CAVEAT,
            "rounds": 1,
            "stopped_because": "single pass",
            "scores": None,
            "warnings": check_brief(result.parsed, evidence.tags()).problems,
            "model": model,
        }
        return brief_markdown(brief, sources)

    def chitchat(_: int, question: str) -> str | None:
        try:
            result = answer_question(question, [], overview, agents, search, loop_settings)
        except StageError:
            return None
        if result.best is None:
            return None
        return brief_markdown(build_brief(question, result, model), sources)

    return {OURS: chitchat, "baseline": baseline}
