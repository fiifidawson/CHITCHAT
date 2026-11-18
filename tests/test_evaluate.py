"""The evaluation harness: question files, imports, blind order and the summary."""

from __future__ import annotations

import random
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from chitchat.evaluate import (
    METRICS,
    OURS,
    Judgement,
    imported_answer,
    parse_import,
    parse_questions,
    run_evaluation,
    summarize,
)
from chitchat.screening.llm import StructuredCaller
from chitchat.stages import StageError


class FavouriteJudge:
    """Scores the answer containing `favourite` 5 and the other 2, and records the prompts."""

    def __init__(self, favourite: str) -> None:
        self.favourite = favourite
        self.prompts: list[str] = []

    def with_structured_output(self, schema: type, include_raw: bool = False) -> Any:
        def invoke(messages: list[Any]) -> dict[str, Any]:
            text = messages[-1].content
            self.prompts.append(text)
            a_text = text.split("=== Answer A ===")[1].split("=== Answer B ===")[0]
            a_wins = self.favourite in a_text
            high = dict.fromkeys(METRICS, 5)
            low = dict.fromkeys(METRICS, 2)
            data = {
                "a": high if a_wins else low,
                "b": low if a_wins else high,
                "winner": "A" if a_wins else "B",
                "reason": "more specific",
            }
            raw = SimpleNamespace(usage_metadata={}, additional_kwargs={})
            return {"raw": raw, "parsed": schema.model_validate(data), "parsing_error": None}

        return SimpleNamespace(invoke=invoke)


def test_parse_questions_skips_comments(tmp_path: Path) -> None:
    path = tmp_path / "q.txt"
    path.write_text("# header\n\nFirst?\n  Second?  \n# note\n", encoding="utf-8")
    assert parse_questions(path) == ["First?", "Second?"]


def test_parse_questions_needs_one(tmp_path: Path) -> None:
    path = tmp_path / "q.txt"
    path.write_text("# only comments\n", encoding="utf-8")
    with pytest.raises(StageError, match="No questions"):
        parse_questions(path)


def test_imports_line_up_with_questions(tmp_path: Path) -> None:
    (tmp_path / "1.md").write_text("answer one", encoding="utf-8")
    (tmp_path / "3.txt").write_text("answer three", encoding="utf-8")
    name, folder = parse_import(f"deepresearch={tmp_path}")
    assert name == "deepresearch"
    assert [imported_answer(folder, n) for n in (1, 2, 3)] == ["answer one", None, "answer three"]


@pytest.mark.parametrize("spec", ["nofolder", "chitchat=.", "bad name=.", "x=does-not-exist"])
def test_bad_imports(spec: str) -> None:
    with pytest.raises(StageError):
        parse_import(spec)


def _systems() -> dict[str, Any]:
    return {
        OURS: lambda n, q: f"OURS answer {n}",
        "baseline": lambda n, q: f"BASE answer {n}",
        "other": lambda n, q: None if n == 2 else f"OTHER answer {n}",
    }


def test_order_is_random_and_unblinded() -> None:
    judge = StructuredCaller(FavouriteJudge("OURS"), Judgement)
    questions = [f"Q{i}?" for i in range(1, 9)]
    answers, judgements = run_evaluation(questions, _systems(), judge, seed=3)
    assert len(answers) == 8 * 3
    # Question 2 has no answer from "other": only the baseline pair is judged.
    assert [j["other"] for j in judgements if j["question_no"] == 2] == ["baseline"]
    orders = {tuple(j["order"]) for j in judgements}
    assert (OURS, "baseline") in orders and ("baseline", OURS) in orders  # both orders occur
    assert all(j["winner"] == OURS for j in judgements)  # unblinded back to the right name
    assert all(j["scores"][OURS]["coverage"] == 5 for j in judgements)
    # The judge never sees system names.
    assert not any("chitchat" in p or "baseline" in p for p in judge.chat_model.prompts)


def test_same_seed_same_order() -> None:
    def orders(seed: int) -> list[list[str]]:
        judge = StructuredCaller(FavouriteJudge("OURS"), Judgement)
        return [j["order"] for j in run_evaluation(["a", "b", "c"], _systems(), judge, seed)[1]]

    assert orders(1) == orders(1)


def test_summary_maths() -> None:
    def j(winner: str, ours: int, theirs: int) -> dict[str, Any]:
        return {
            "other": "baseline",
            "status": "ok",
            "winner": winner,
            "scores": {
                OURS: dict.fromkeys(METRICS, ours),
                "baseline": dict.fromkeys(METRICS, theirs),
            },
        }

    judgements = [
        j(OURS, 5, 3),
        j("tie", 3, 3),
        j("baseline", 2, 4),
        {"other": "baseline", "status": "invalid"},
    ]
    text = summarize(judgements, {"questions": 4})
    assert "3 questions judged: 1 wins, 1 ties, 1 losses." in text
    assert "1 judgements failed" in text
    assert "| coverage | 3.33 | 3.33 | +0.00 |" in text


def test_judge_scores_are_clamped() -> None:
    side = dict.fromkeys(METRICS, 9)
    j = Judgement.model_validate({"a": side, "b": side, "winner": "tie", "reason": "x"})
    assert j.a.coverage == 5


def test_random_is_seeded() -> None:
    assert random.Random(0).random() == random.Random(0).random()
