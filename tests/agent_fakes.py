"""Fakes for the answer loop: a scripted chat model and an in-memory index."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from chitchat.agents.schemas import Scores


class ScriptedModel:
    """Returns scripted outputs per schema name and records each call's messages."""

    def __init__(self, **outputs: list[dict[str, Any] | None]) -> None:
        self.outputs = {name: list(items) for name, items in outputs.items()}
        self.calls: list[tuple[str, list[Any]]] = []

    def with_structured_output(self, schema: type, include_raw: bool = False) -> Any:
        def invoke(messages: list[Any]) -> dict[str, Any]:
            self.calls.append((schema.__name__, messages))
            data = self.outputs[schema.__name__].pop(0)
            raw = SimpleNamespace(usage_metadata={}, additional_kwargs={})
            if data is None:
                return {"raw": raw, "parsed": None, "parsing_error": "bad json"}
            return {"raw": raw, "parsed": schema.model_validate(data), "parsing_error": None}

        return SimpleNamespace(invoke=invoke)

    def kinds(self) -> list[str]:
        return [name for name, _ in self.calls]

    def prompt(self, i: int) -> str:
        return "\n".join(m.content for m in self.calls[i][1])


class FakeIndex:
    """`search(query, k)` over fixed passages. A query sees the passages whose words it shares."""

    def __init__(self, passages: dict[str, tuple[str, str]]) -> None:
        self.passages = passages  # chunk id -> (tag, text)
        self.queries: list[str] = []

    def __call__(self, query: str, k: int) -> list[Any]:
        self.queries.append(query)
        words = set(query.lower().split())
        hits = [
            {"page_content": f"[{tag}] {text}", "metadata": {"id": cid, "file_path": tag}}
            for cid, (tag, text) in self.passages.items()
            if words & set(text.lower().split())
        ]
        return hits[:k]


PLAN = {
    "decision": "Whether to use chatbots for refugee intake",
    "options": ["chatbot", "human caseworkers"],
    "criteria": ["accuracy", "do no harm"],
    "sub_questions": [
        {"question": "chatbot accuracy", "purpose": "benefits"},
        {"question": "chatbot harms", "purpose": "risks"},
    ],
}


def _draft(tag: str = "P0001", support: str = "evidence") -> dict[str, Any]:
    return {
        "bottom_line": "Chatbots help with volume but need human checks.",
        "options": [
            {
                "name": "chatbot",
                "description": "Automated intake.",
                "benefits": [{"text": "Faster intake.", "sources": [tag], "support": support}],
                "risks": [],
                "evidence_strength": "moderate",
            },
            {
                "name": "human caseworkers",
                "description": "Current practice.",
                "benefits": [],
                "risks": [],
                "evidence_strength": "insufficient",
            },
        ],
        "tradeoffs": [
            {
                "criterion": "accuracy",
                "assessments": [
                    {"option": "chatbot", "assessment": "Good on simple cases", "sources": [tag]},
                    {"option": "human caseworkers", "assessment": "Best", "sources": []},
                ],
            }
        ],
        "conflicts": [
            {
                "issue": "Error rates",
                "positions": [{"text": "Low errors", "sources": [tag]}],
                "conflict_type": "context",
            }
        ],
        "considerations": [
            {"priority": "speed", "option": "chatbot", "because": "it scales", "sources": [tag]}
        ],
        "gaps": ["No studies in camps."],
    }


def _critique(verdict: str, score: int = 1, follow_ups: list[str] | None = None) -> dict:
    scores = {name: score for name in Scores.model_fields}
    issues = [] if verdict == "accept" else [{"problem": "Thin on harms.", "fix": "Add harms."}]
    return {
        "verdict": verdict,
        "scores": scores,
        "issues": issues,
        "follow_up_queries": follow_ups or [],
    }


INDEX = {
    "c1": ("P0001", "chatbot accuracy was high for intake"),
    "c2": ("P0002", "chatbot harms include privacy leaks"),
    "c3": ("D0001", "field notes on caseworkers and trust"),
}
