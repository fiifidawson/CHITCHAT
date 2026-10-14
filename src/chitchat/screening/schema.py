"""Pydantic answer models, built at runtime from the criteria.

Scores are string literals ("0", "1", ...), because provider support for
`int | str` unions is patchy. They are converted to int after parsing.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, create_model

from chitchat.screening.criteria import Criteria, Criterion, ExtractField
from chitchat.screening.rules import UNCLEAR

EVIDENCE_HELP = "A short quote from the paper, under 300 characters. Empty when unclear."
NOTES_HELP = "Anything worth flagging to the reviewer. Empty if nothing."
EVIDENCE_MAX = 300


def _describe(c: Criterion) -> str:
    if not c.scale:
        return c.question
    scale = "; ".join(f"{k} = {v}" for k, v in c.scale.items())
    return f"{c.question} Scale: {scale}."


def _model_name(cid: str) -> str:
    return "".join(part.capitalize() for part in cid.split("_")) + "Answer"


def answer_model(c: Criterion) -> type[BaseModel]:
    if c.type == "yes_no":
        answer_type: Any = Literal["yes", "no", "unclear"]
    elif c.type == "score":
        answer_type = Literal[tuple([str(k) for k in c.scale or {}] + [UNCLEAR])]
    else:
        answer_type = str
    return create_model(
        _model_name(c.id),
        answer=(answer_type, Field(description=_describe(c))),
        evidence=(str, Field(description=EVIDENCE_HELP)),
    )


def screening_model(criteria: Criteria) -> type[BaseModel]:
    fields: dict[str, Any] = {
        c.id: (answer_model(c), Field(description=_describe(c))) for c in criteria.criteria
    }
    fields["notes"] = (str, Field(description=NOTES_HELP))
    return create_model("ScreeningAnswers", **fields)


def _extract_answer_model(f: ExtractField) -> type[BaseModel]:
    answer_type: Any = {"list": list[str] | None, "number": float | None, "text": str | None}[
        f.type
    ]
    return create_model(
        _model_name(f.id),
        answer=(answer_type, Field(description=f"{f.question} Null if not reported.")),
        evidence=(str, Field(description=EVIDENCE_HELP)),
    )


def extraction_model(criteria: Criteria) -> type[BaseModel] | None:
    if not criteria.extract:
        return None
    fields: dict[str, Any] = {
        f.id: (_extract_answer_model(f), Field(description=f.question)) for f in criteria.extract
    }
    return create_model("ExtractedFields", **fields)


def _evidence(value: str) -> str:
    value = " ".join((value or "").split())
    return value if len(value) <= EVIDENCE_MAX else value[: EVIDENCE_MAX - 1] + "…"


def normalize_answers(parsed: BaseModel, criteria: Criteria) -> dict[str, dict[str, Any]]:
    """`{id: {answer, evidence}}` with scores as int."""
    out: dict[str, dict[str, Any]] = {}
    for c in criteria.criteria:
        item = getattr(parsed, c.id)
        answer: Any = item.answer
        if c.type == "score" and answer != UNCLEAR:
            answer = int(answer)
        out[c.id] = {
            "answer": answer,
            "evidence": "" if answer == UNCLEAR else _evidence(item.evidence),
        }
    return out


def normalize_extracted(parsed: BaseModel, criteria: Criteria) -> dict[str, dict[str, Any]]:
    return {
        f.id: {
            "answer": getattr(parsed, f.id).answer,
            "evidence": _evidence(getattr(parsed, f.id).evidence),
        }
        for f in criteria.extract
    }


def answer_values(answers: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """`{id: answer}` for the rules."""
    return {cid: item.get("answer") for cid, item in answers.items()}
