"""Checks on a draft brief, by code. They run before the Critic and can force a rewrite."""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass, field

from chitchat.agents.schemas import BriefDraft, Claim

TAG = re.compile(r"\b([PD]\d{4})\b")


@dataclass
class CheckResult:
    problems: list[str] = field(default_factory=list)
    unknown_tags: list[str] = field(default_factory=list)

    @property
    def blocking(self) -> bool:
        """Citations to passages the Writer never saw: always rewrite."""
        return bool(self.unknown_tags)


def _claims(draft: BriefDraft) -> Iterator[tuple[str, Claim]]:
    for option in draft.options:
        for claim in option.benefits:
            yield f"benefit of {option.name!r}", claim
        for claim in option.risks:
            yield f"risk of {option.name!r}", claim
    for conflict in draft.conflicts:
        for claim in conflict.positions:
            yield f"position in conflict {conflict.issue!r}", claim


def cited_tags(draft: BriefDraft) -> list[str]:
    """Every tag the brief cites, in `sources` fields or inside its text, in order."""
    found: list[str] = []
    found += TAG.findall(draft.bottom_line)
    for _, claim in _claims(draft):
        found += [*claim.sources, *TAG.findall(claim.text)]
    for option in draft.options:
        found += TAG.findall(option.description)
    for row in draft.tradeoffs:
        for a in row.assessments:
            found += [*a.sources, *TAG.findall(a.assessment)]
    for c in draft.considerations:
        found += [*c.sources, *TAG.findall(c.because)]
    return list(dict.fromkeys(t.strip("[] ") for t in found))


def check_brief(draft: BriefDraft, known_tags: set[str]) -> CheckResult:
    result = CheckResult()
    result.unknown_tags = [t for t in cited_tags(draft) if t not in known_tags]
    if result.unknown_tags:
        result.problems.append(
            "cites sources that are not in the evidence: " + ", ".join(result.unknown_tags)
        )
    for where, claim in _claims(draft):
        if claim.support == "evidence" and not claim.sources:
            result.problems.append(
                f"{where} is marked as evidence but has no source: {claim.text[:80]!r}"
            )
    for option in draft.options:
        sourced = any(c.sources for c in [*option.benefits, *option.risks])
        if not sourced and option.evidence_strength != "insufficient":
            result.problems.append(
                f"option {option.name!r} has no sourced benefit or risk, "
                f"but its evidence strength is {option.evidence_strength!r}"
            )
    return result
