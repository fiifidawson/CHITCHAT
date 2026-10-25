"""What each agent returns. The LLM fills these through structured output."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, Field

Purpose = Literal["options", "benefits", "risks", "context", "gaps"]
Support = Literal["evidence", "hypothesis"]
Strength = Literal["strong", "moderate", "weak", "insufficient"]
# DeepEvidence's taxonomy: stronger vs weaker study designs, different settings, or noise.
ConflictType = Literal["hierarchy", "context", "noise"]
Verdict = Literal["accept", "revise"]

CAVEAT = (
    "This brief is an aid to a decision, not the decision. It covers only the papers and "
    "documents in this run; check the cited sources before acting."
)


# --- Planner -------------------------------------------------------------------------------


class SubQuestion(BaseModel):
    question: str = Field(description="A short search question for the index.")
    purpose: Purpose


class Plan(BaseModel):
    decision: str = Field(description="The decision the researcher faces, in one sentence.")
    options: list[str] = Field(description="2 to 4 options to compare, a few words each.")
    criteria: list[str] = Field(description="What the options should be judged on.")
    sub_questions: list[SubQuestion] = Field(description="4 to 6 questions to search for.")


# --- Writer --------------------------------------------------------------------------------


class Claim(BaseModel):
    text: str
    sources: list[str] = Field(default_factory=list, description="Tags such as P0007 or D0002.")
    support: Support = Field(
        "evidence", description="evidence: the cited passages say it. hypothesis: your inference."
    )


class Option(BaseModel):
    name: str
    description: str
    benefits: list[Claim] = Field(default_factory=list)
    risks: list[Claim] = Field(default_factory=list)
    evidence_strength: Strength


class Assessment(BaseModel):
    option: str
    assessment: str
    sources: list[str] = Field(default_factory=list)


class Tradeoff(BaseModel):
    criterion: str
    assessments: list[Assessment] = Field(description="One per option.")


class Conflict(BaseModel):
    issue: str
    positions: list[Claim]
    conflict_type: ConflictType


class Consideration(BaseModel):
    priority: str = Field(description="What the researcher might care about most.")
    option: str
    because: str
    sources: list[str] = Field(default_factory=list)


class BriefDraft(BaseModel):
    """The Writer's output. The stage adds the question, caveat and loop details."""

    bottom_line: str = Field(description="2 or 3 sentences.")
    options: list[Option]
    tradeoffs: list[Tradeoff] = Field(default_factory=list)
    conflicts: list[Conflict] = Field(default_factory=list)
    considerations: list[Consideration] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list, description="What the evidence doesn't cover.")


# --- Critic --------------------------------------------------------------------------------


def _clamp(value: object) -> object:
    """Small models sometimes answer 3 or -1. Keep the score on the 0–2 scale."""
    try:
        return min(2, max(0, int(value)))  # type: ignore[call-overload]
    except (TypeError, ValueError):
        return value


Score = Annotated[int, BeforeValidator(_clamp)]

RUBRIC = (
    "coverage",
    "groundedness",
    "conflict_handling",
    "uncertainty",
    "humanitarian_awareness",
    "specificity",
)


class Scores(BaseModel):
    """0 = poor, 1 = partly, 2 = good (DeepEvidence's 0–2 expert scale)."""

    coverage: Score = Field(description="Sub-questions and options covered.")
    groundedness: Score = Field(description="Claims match the cited passages.")
    conflict_handling: Score = Field(description="Disagreements named and explained.")
    uncertainty: Score = Field(description="Evidence strength stated honestly.")
    humanitarian_awareness: Score = Field(
        description="Do no harm, impartiality, affected people's rights."
    )
    specificity: Score = Field(description="Concrete, not generic.")

    def total(self) -> int:
        return sum(getattr(self, name) for name in RUBRIC)


class Issue(BaseModel):
    problem: str
    fix: str


class Critique(BaseModel):
    verdict: Verdict
    scores: Scores
    issues: list[Issue] = Field(default_factory=list)
    follow_up_queries: list[str] = Field(
        default_factory=list, description="Up to 3 searches for missing evidence."
    )
