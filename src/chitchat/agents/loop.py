"""The answer loop: plan, retrieve, write, check and critique, then revise.

Plain Python with an explicit state. Every LLM step returns a schema from `schemas.py`.
Only masked text reaches the LLM: the question was masked when the search was planned,
and the passages were sanitized before indexing.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from chitchat.agents import prompts
from chitchat.agents.checks import CheckResult, check_brief
from chitchat.agents.retrieval import Evidence, Search
from chitchat.agents.schemas import BriefDraft, Critique, Plan
from chitchat.screening.llm import CallResult, StructuredCaller
from chitchat.stages import StageError

Trace = Callable[[dict[str, Any]], None]


@dataclass
class LoopSettings:
    max_rounds: int = 3
    k_per_query: int = 6
    max_evidence_chars: int = 24_000


class Agents:
    """The three LLM agents, sharing one chat model."""

    def __init__(self, chat_model: Any, method: str = "json_schema") -> None:
        self.planner = StructuredCaller(chat_model, Plan, method)
        self.writer = StructuredCaller(chat_model, BriefDraft, method)
        self.critic = StructuredCaller(chat_model, Critique, method)


@dataclass
class Round:
    number: int
    draft: BriefDraft
    checks: CheckResult
    critique: Critique | None = None
    new_evidence: int = 0  # passages added before this draft was written

    @property
    def score(self) -> int:
        return self.critique.scores.total() if self.critique else -1


@dataclass
class LoopResult:
    plan: Plan
    evidence: Evidence
    rounds: list[Round] = field(default_factory=list)
    stopped_because: str = ""
    best: Round | None = None


def _call(caller: StructuredCaller, messages: list[Any], role: str, n: int, trace: Trace) -> Any:
    start = time.perf_counter()
    result: CallResult = caller(messages)
    trace(
        {
            "round": n,
            "role": role,
            "status": result.status,
            "seconds": round(time.perf_counter() - start, 2),
            "usage": result.usage,
            "error": result.error,
            "output": result.parsed.model_dump() if result.parsed is not None else None,
        }
    )
    return result.parsed if result.status == "ok" else None


def _retrieve(
    search: Search, queries: list[str], k: int, evidence: Evidence, n: int, trace: Trace
) -> int:
    start = time.perf_counter()
    added = 0
    for query in queries:
        added += evidence.add(search(query, k), query)
    trace(
        {
            "round": n,
            "role": "retriever",
            "status": "ok",
            "seconds": round(time.perf_counter() - start, 2),
            "queries": queries,
            "new_passages": added,
            "total_passages": len(evidence.passages),
            "dropped_by_cap": evidence.dropped,
        }
    )
    return added


def answer_question(
    question: str,
    clarifications: list[tuple[str, str]],
    overview: str,
    agents: Agents,
    search: Search,
    settings: LoopSettings,
    trace: Trace = lambda event: None,
) -> LoopResult:
    """Run the loop. Raises StageError if the Planner or the first Writer call fails."""
    plan = _call(
        agents.planner,
        prompts.planner_messages(question, clarifications, overview),
        "planner",
        0,
        trace,
    )
    if plan is None:
        raise StageError("The Planner couldn't make a plan. See answer/trace.jsonl.")

    evidence = Evidence(settings.max_evidence_chars)
    queries = [question, *(s.question for s in plan.sub_questions)]
    new = _retrieve(search, queries, settings.k_per_query, evidence, 1, trace)

    state = LoopResult(plan=plan, evidence=evidence)
    previous: Round | None = None
    for n in range(1, settings.max_rounds + 1):
        messages = prompts.writer_messages(
            question,
            clarifications,
            plan,
            evidence.render(),
            critique=previous.critique if previous else None,
            checks=previous.checks.problems if previous else None,
            draft=previous.draft if previous else None,
        )
        draft = _call(agents.writer, messages, "writer", n, trace)
        if draft is None:
            if previous is None:
                raise StageError("The Writer couldn't write a brief. See answer/trace.jsonl.")
            state.stopped_because = "the Writer failed; kept the previous draft"
            break

        checks = check_brief(draft, evidence.tags())
        trace({"round": n, "role": "checks", "status": "ok", "problems": checks.problems})
        critique = _call(
            agents.critic,
            prompts.critic_messages(question, plan, evidence.render(), draft, checks.problems),
            "critic",
            n,
            trace,
        )
        current = Round(n, draft, checks, critique, new)
        state.rounds.append(current)
        if critique is None:
            state.stopped_because = "the Critic failed; kept this draft"
            break
        if critique.verdict == "accept" and not checks.blocking:
            state.stopped_because = "accepted by the Critic"
            break
        if previous and current.new_evidence == 0 and current.score <= previous.score:
            state.stopped_because = "no new evidence and no better score"
            break
        if n == settings.max_rounds:
            state.stopped_because = f"reached the round limit ({settings.max_rounds})"
            break
        follow_ups = critique.follow_up_queries[:3]
        new = _retrieve(search, follow_ups, settings.k_per_query, evidence, n + 1, trace)
        previous = current

    state.best = _best(state.rounds)
    return state


def _best(rounds: list[Round]) -> Round | None:
    """The draft to keep: valid citations first, then the highest score, then the latest."""
    if not rounds:
        return None
    return max(rounds, key=lambda r: (not r.checks.blocking, r.score, r.number))
