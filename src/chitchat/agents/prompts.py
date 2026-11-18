"""One system prompt per agent, and the messages each one gets."""

from __future__ import annotations

from typing import Any

from chitchat.agents.schemas import BriefDraft, Critique, Plan

PRINCIPLES = (
    "humanity, impartiality, neutrality, independence, do no harm, "
    "and the rights and dignity of affected people"
)

PLANNER_SYSTEM = f"""You plan the answer to a researcher's question for a literature review
in the humanitarian sector. The researcher wants to make an informed decision.

Return:
- decision: the decision the researcher faces, in one sentence.
- options: 2 to 4 realistic options to compare (include "do nothing / current practice" when
  it makes sense). A few words each.
- criteria: what the options should be judged on. Always include the humanitarian principles
  that matter here ({PRINCIPLES}), plus practical ones such as cost, feasibility, accuracy.
- sub_questions: 4 to 6 short questions to search the review's index for. Tag each with its
  purpose: options, benefits, risks, context or gaps. Cover every option.
"""

WRITER_SYSTEM = """You write a decision brief from the evidence of a literature review.

Rules:
- Use only the evidence passages. Each passage starts with a source tag such as [P0007].
- Put tags in `sources` as plain tags, such as P0007. Cite only tags that appear in the evidence.
- support "evidence": the cited passages say it. support "hypothesis": your own reasoning;
  label it honestly. Never cite a source for something it does not say.
- Give each option its benefits and risks, and an honest evidence_strength:
  strong (several consistent sources), moderate, weak (one source or indirect),
  insufficient (no evidence).
- tradeoffs: one row per criterion, with an assessment for every option.
- conflicts: where sources disagree. conflict_type is "hierarchy" (stronger vs weaker study
  designs), "context" (different settings or populations) or "noise" (small, old or unclear
  studies).
- considerations: "if this priority matters most, prefer this option, because ...".
- gaps: what the evidence does not cover.
- Be specific: name settings, populations, numbers and harms from the passages.
- bottom_line: 2 or 3 sentences that answer the question directly.
"""

CRITIC_SYSTEM = f"""You review a decision brief written from literature-review evidence.
Score each dimension 0 (poor), 1 (partly) or 2 (good):
- coverage: the plan's sub-questions and every option are covered.
- groundedness: each claim is supported by the passages it cites.
- conflict_handling: disagreements between sources are named and explained.
- uncertainty: evidence strength and hypotheses are stated honestly.
- humanitarian_awareness: {PRINCIPLES} are weighed.
- specificity: concrete settings, numbers and harms, not generic statements.

verdict "accept" if the brief is good enough to help a decision and nothing important is wrong.
Otherwise "revise", with issues (problem and fix) and up to 3 follow_up_queries: short searches
for evidence the brief is missing. Automatic checks found by code are listed; treat them as true.
"""


def _messages(system: str, user: str) -> list[Any]:
    from langchain_core.messages import HumanMessage, SystemMessage

    return [SystemMessage(content=system), HumanMessage(content=user)]


def _question_block(question: str, clarifications: list[tuple[str, str]]) -> str:
    lines = [f"Question: {question}"]
    answered = [(q, a) for q, a in clarifications if a.strip()]
    if answered:
        lines.append("Clarifications from the researcher:")
        lines += [f"- {q} {a}" for q, a in answered]
    return "\n".join(lines)


def planner_messages(
    question: str, clarifications: list[tuple[str, str]], overview: str
) -> list[Any]:
    user = f"{_question_block(question, clarifications)}\n\nWhat the review holds:\n{overview}"
    return _messages(PLANNER_SYSTEM, user)


def writer_messages(
    question: str,
    clarifications: list[tuple[str, str]],
    plan: Plan,
    evidence: str,
    critique: Critique | None = None,
    checks: list[str] | None = None,
    draft: BriefDraft | None = None,
) -> list[Any]:
    parts = [
        _question_block(question, clarifications),
        f"Plan:\n{plan.model_dump_json(indent=1)}",
        f"Evidence:\n{evidence or '(none found)'}",
    ]
    if draft is not None:
        parts.append(f"Your previous brief:\n{draft.model_dump_json()}")
    if critique is not None:
        issues = "\n".join(f"- {i.problem} Fix: {i.fix}" for i in critique.issues) or "- none"
        parts.append(f"Reviewer's issues:\n{issues}")
    if checks:
        parts.append("Automatic checks failed:\n" + "\n".join(f"- {c}" for c in checks))
    if draft is not None:
        parts.append("Rewrite the whole brief and fix every issue.")
    return _messages(WRITER_SYSTEM, "\n\n".join(parts))


def critic_messages(
    question: str, plan: Plan, evidence: str, draft: BriefDraft, checks: list[str]
) -> list[Any]:
    found = "\n".join(f"- {c}" for c in checks) or "- none"
    user = "\n\n".join(
        [
            f"Question: {question}",
            f"Plan:\n{plan.model_dump_json(indent=1)}",
            f"Evidence:\n{evidence or '(none found)'}",
            f"Brief:\n{draft.model_dump_json(indent=1)}",
            f"Automatic checks:\n{found}",
        ]
    )
    return _messages(CRITIC_SYSTEM, user)
