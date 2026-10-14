from __future__ import annotations

import inspect

import pytest

from chitchat.screening import rules
from chitchat.screening.rules import Rule, decide, holds, parse_condition

TYPES = {"ok": "yes_no", "q": "score"}
SCALES = {"q": 3}


def c(text: str):
    return parse_condition(text, TYPES, SCALES)


@pytest.mark.parametrize(
    ("cond", "answer", "expected"),
    [
        ("q == 2", 2, True),
        ("q == 2", 3, False),
        ("q != 2", 3, True),
        ("q >= 2", 2, True),
        ("q >= 2", 1, False),
        ("q <= 2", 2, True),
        ("q <= 2", 3, False),
        ("q > 2", 3, True),
        ("q > 2", 2, False),
        ("q < 2", 1, True),
        ("q < 2", 2, False),
        ("ok == yes", "yes", True),
        ("ok != yes", "no", True),
        ("ok == unclear", "unclear", True),
    ],
)
def test_operators(cond: str, answer, expected: bool) -> None:
    assert holds(c(cond), answer) is expected


@pytest.mark.parametrize("cond", ["q >= 0", "q <= 3", "q > 0", "q < 3"])
def test_unclear_never_satisfies_ordering(cond: str) -> None:
    assert holds(c(cond), "unclear") is False


def test_unclear_equality_works() -> None:
    assert holds(c("q == unclear"), "unclear")
    assert holds(c("q != unclear"), 2)


def test_first_match_wins_and_because() -> None:
    rules_ = [
        Rule("EXCLUDE", (c("ok == no"),)),
        Rule("HIGH", (c("ok == yes"), c("q >= 2"))),
        Rule("MEDIUM", (c("ok == yes"),)),
        Rule("LOW", ()),
    ]
    assert decide(rules_, {"ok": "yes", "q": 3}) == {
        "label": "HIGH",
        "rule_index": 1,
        "because": ["ok == yes (was yes)", "q >= 2 (was 3)"],
    }
    assert decide(rules_, {"ok": "yes", "q": "unclear"})["label"] == "MEDIUM"
    assert decide(rules_, {"ok": "no", "q": 3})["label"] == "EXCLUDE"


def test_default_rule_and_missing_answers() -> None:
    rules_ = [Rule("HIGH", (c("q >= 1"),)), Rule("LOW", ())]
    out = decide(rules_, {})
    assert out == {"label": "LOW", "rule_index": 1, "because": ["default"]}


def test_no_eval() -> None:
    source = inspect.getsource(rules)
    assert "eval(" not in source and "exec(" not in source
