"""Screening criteria drafted from the researcher's question, like the search itself.

The LLM writes yes/no questions only. Code turns them into fixed rules, so every drafted file
works the same way:
- a paper is EXCLUDE if it answers "no" to a `must` question or "yes" to an `exclude` one;
- HIGH if it answers "yes" to every `stronger` question, MEDIUM if to at least one, else LOW.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from chitchat.search.plan import SearchPlan

CRITERIA_SYSTEM = """You write the screening criteria for a literature review.
A model will read each paper the search finds and answer your questions about it, so each
question must be answerable from the paper's text.

Return:
- context: one or two sentences on what the review is about, for the model that screens.
- must: 1 to 3 yes/no questions a paper must answer "yes" to, to be relevant. Keep them as broad
  as the question: a paper on the topic, in any setting or design, should pass. Never require a
  technology, method or population the question and the researcher's answers don't require.
- exclude: 0 to 2 yes/no questions where "yes" means the paper is out, for things the researcher
  ruled out. Leave it empty if they ruled nothing out.
- stronger: 2 to 4 yes/no questions where "yes" makes a paper more useful for the decision,
  such as reporting real data, a setting close to the researcher's, or outcomes and harms.
- extract: 2 to 4 short questions whose answers are pulled from each relevant paper for the
  review table, such as the approach used, the population, the setting, what went wrong.

Rules:
- One idea per question. Plain words. No double negatives.
- `id` is a short snake_case name for the question, such as consent_process.
"""


class ScreeningQuestion(BaseModel):
    id: str = Field(description="A short snake_case name, such as consent_process.")
    question: str


class CriteriaDraft(BaseModel):
    context: str
    must: list[ScreeningQuestion] = Field(description="1 to 3 questions a relevant paper passes.")
    exclude: list[ScreeningQuestion] = Field(description="0 to 2 questions; yes = out.")
    stronger: list[ScreeningQuestion] = Field(description="2 to 4 questions; yes = more useful.")
    extract: list[ScreeningQuestion] = Field(description="2 to 4 questions answered per paper.")


# --- Messages ---------------------------------------------------------------------------------


def criteria_messages(
    question: str, clarifications: list[tuple[str, str]], plan: SearchPlan
) -> list[Any]:
    from langchain_core.messages import HumanMessage, SystemMessage

    lines = [f"Research question: {question}"]
    answered = [(q, a) for q, a in clarifications if a.strip()]
    if answered:
        lines.append("\nClarifications from the researcher:")
        lines += [f"- {q} {a}" for q, a in answered]
    lines.append("\nThe search covers: " + "; ".join(c.name for c in plan.categories))
    return [SystemMessage(content=CRITERIA_SYSTEM), HumanMessage(content="\n".join(lines))]


def add_criteria_feedback(messages: list[Any], draft: CriteriaDraft, feedback: str) -> list[Any]:
    from langchain_core.messages import AIMessage, HumanMessage

    return [
        *messages,
        AIMessage(content=draft.model_dump_json()),
        HumanMessage(content=f"Revise all the criteria. Change request: {feedback}"),
    ]


# --- The criteria file -----------------------------------------------------------------------

_NOT_ID = re.compile(r"[^a-z0-9_]+")


def _ids(questions: list[ScreeningQuestion], seen: set[str]) -> list[tuple[str, str]]:
    """(snake_case id, question) pairs, with ids made valid and unique."""
    out = []
    for q in questions:
        text = " ".join(q.question.split())
        if not text:
            continue
        base = _NOT_ID.sub("_", q.id.lower()).strip("_") or "question"
        base = base if base[0].isalpha() else f"q_{base}"
        cid, n = base[:40], 2
        while cid in seen:
            cid, n = f"{base[:37]}_{n}", n + 1
        seen.add(cid)
        out.append((cid, text))
    return out


def criteria_file(draft: CriteriaDraft, name: str, question: str) -> dict[str, Any]:
    """A criteria file (the same format as configs/criteria.example.yaml) from a draft."""
    seen: set[str] = set()
    must, exclude, stronger = (_ids(qs, seen) for qs in (draft.must, draft.exclude, draft.stronger))
    extract = _ids(draft.extract, seen)
    yes_no = [*must, *exclude, *stronger]
    decision: list[dict[str, Any]] = [
        *({"label": "EXCLUDE", "when": [f"{cid} == no"]} for cid, _ in must),
        *({"label": "EXCLUDE", "when": [f"{cid} == yes"]} for cid, _ in exclude),
    ]
    if stronger:
        decision.append({"label": "HIGH", "when": [f"{cid} == yes" for cid, _ in stronger]})
        decision += [{"label": "MEDIUM", "when": [f"{cid} == yes"]} for cid, _ in stronger]
    decision.append({"label": "LOW"})
    context = " ".join(draft.context.split())
    return {
        "name": name,
        "version": 1,
        "context": f"{context}\nThe researcher's question: {question}".strip(),
        "criteria": [{"id": cid, "question": q, "type": "yes_no"} for cid, q in yes_no],
        "decision": decision,
        "extract": [{"id": cid, "question": q, "type": "text"} for cid, q in extract],
    }


def write_criteria(path: Path, data: dict[str, Any]) -> Path:
    from chitchat.screening.criteria import parse_criteria

    parse_criteria(data)  # the same checks as a hand-written file
    path.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "# Drafted by `chitchat search` from your question and answers. Edit it if you like:\n"
        "# change only `decision`, then `chitchat run --redecide` relabels with no LLM calls.\n"
    )
    path.write_text(
        header + yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    return path


# --- The conversation ------------------------------------------------------------------------


def criteria_view(draft: CriteriaDraft) -> Any:
    from rich.console import Group
    from rich.text import Text

    from chitchat import ui

    def section(title: str, rule: str, questions: list[ScreeningQuestion]) -> list[Text]:
        if not questions:
            return []
        lines = [Text(title, style="bold"), Text(rule, style="dim")]
        lines += [Text(f"  · {q.question}") for q in questions]
        return [*lines, Text("")]

    body = [
        *section("Must be true", "A paper that answers no is excluded.", draft.must),
        *section("Rules a paper out", "A paper that answers yes is excluded.", draft.exclude),
        *section(
            "Makes a paper stronger",
            "Yes to all: HIGH. Yes to some: MEDIUM. None: LOW.",
            draft.stronger,
        ),
        *section("Pulled from each paper", "Goes into dataset.csv.", draft.extract),
    ]
    return ui.boxed("Screening criteria", Group(*body[:-1]))  # no blank line at the end


def draft_criteria(
    question: str,
    clarifications: list[tuple[str, str]],
    plan: SearchPlan,
    drafter: Any,
    io: Any,
    mask: Any = lambda text: text,
    auto_accept: bool = False,
) -> tuple[CriteriaDraft, dict[str, Any]] | None:
    """Draft the criteria, then accept / change / quit. Returns None on quit."""
    from rich.text import Text

    from chitchat import ui

    log: dict[str, Any] = {"turns": []}
    messages = criteria_messages(question, clarifications, plan)
    while True:
        with ui.console.status("Drafting the screening criteria…", spinner_style=ui.ACCENT):
            draft = drafter.criteria(messages)
        turn: dict[str, Any] = {"draft": draft.model_dump()}
        log["turns"].append(turn)
        io.show(criteria_view(draft))

        feedback = ""
        while not feedback:
            if auto_accept:
                choice = "a"
            else:
                io.show(Text("[a] accept   [c] ask for changes   [q] quit", style="bold"))
                choice = io.choose("Your choice", ["a", "c", "q"], default="a")
            if choice == "a":
                log["accepted"] = draft.model_dump()
                return draft, log
            if choice == "q":
                return None
            feedback = mask(io.ask("What should change?").strip())
        turn["feedback"] = feedback
        messages = add_criteria_feedback(messages, draft, feedback)
