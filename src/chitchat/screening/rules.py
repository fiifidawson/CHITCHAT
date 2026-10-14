"""Decision rules: `<id> <op> <value>`, all conditions in a rule must hold.

A tiny hand-written parser. No eval.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

UNCLEAR = "unclear"
YES_NO_VALUES = ("yes", "no", UNCLEAR)
ORDER_OPS = (">=", "<=", ">", "<")

_CONDITION = re.compile(r"^\s*([a-z][a-z0-9_]*)\s*(==|!=|>=|<=|>|<)\s*([A-Za-z0-9_]+)\s*$")


class RuleError(ValueError):
    """A rule that can't be parsed or doesn't fit the criteria."""


@dataclass(frozen=True)
class Condition:
    id: str
    op: str
    value: str | int
    text: str


@dataclass(frozen=True)
class Rule:
    label: str
    conditions: tuple[Condition, ...]  # empty = the default rule


def parse_condition(text: str, types: dict[str, str], scales: dict[str, int]) -> Condition:
    """Parse one condition. `types` maps criterion id to type; `scales` maps score id to max."""
    match = _CONDITION.match(text)
    if not match:
        raise RuleError(f"can't read condition {text!r}; expected `<id> <op> <value>`")
    cid, op, raw = match.groups()
    kind = types.get(cid)
    if kind is None:
        raise RuleError(f"condition {text!r} uses unknown criterion {cid!r}")
    if kind == "yes_no":
        if raw not in YES_NO_VALUES:
            raise RuleError(f"condition {text!r}: {cid} is yes_no, so use yes, no or unclear")
        if op in ORDER_OPS:
            raise RuleError(f"condition {text!r}: use == or != with yes_no criteria")
        return Condition(cid, op, raw, text.strip())
    if kind == "score":
        if raw == UNCLEAR:
            if op in ORDER_OPS:
                raise RuleError(f"condition {text!r}: use == or != with unclear")
            return Condition(cid, op, raw, text.strip())
        if not raw.isdigit() or int(raw) > scales[cid]:
            raise RuleError(f"condition {text!r}: value must be 0..{scales[cid]} or unclear")
        return Condition(cid, op, int(raw), text.strip())
    raise RuleError(f"condition {text!r}: {kind} criteria can't be used in rules")


def holds(cond: Condition, answer: Any) -> bool:
    if cond.op == "==":
        return answer == cond.value
    if cond.op == "!=":
        return answer != cond.value
    # `unclear` (or anything not a number) never satisfies an ordering.
    if not isinstance(answer, int) or isinstance(answer, bool):
        return False
    value = int(cond.value)
    return {
        ">=": answer >= value,
        "<=": answer <= value,
        ">": answer > value,
        "<": answer < value,
    }[cond.op]


def decide(rules: list[Rule], answers: dict[str, Any]) -> dict[str, Any]:
    """First matching rule wins. `answers` maps id to answer value; missing means unclear."""
    for index, rule in enumerate(rules):
        values = [answers.get(c.id, UNCLEAR) for c in rule.conditions]
        if all(holds(c, v) for c, v in zip(rule.conditions, values, strict=True)):
            because = [f"{c.text} (was {v})" for c, v in zip(rule.conditions, values, strict=True)]
            return {"label": rule.label, "rule_index": index, "because": because or ["default"]}
    raise RuleError("no rule matched; the criteria file needs a default rule")
