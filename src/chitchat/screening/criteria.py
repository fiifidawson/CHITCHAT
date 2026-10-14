"""Load and check a criteria file."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from chitchat.config import LABELS
from chitchat.screening.rules import Rule, RuleError, parse_condition

CRITERION_TYPES = ("yes_no", "score", "text")
EXTRACT_TYPES = ("list", "text", "number")
_ID = re.compile(r"^[a-z][a-z0-9_]*$")


class CriteriaError(ValueError):
    """A problem in a criteria file. The message names the field at fault."""


@dataclass(frozen=True)
class Criterion:
    id: str
    question: str
    type: str
    scale: dict[int, str] | None = None

    @property
    def max_score(self) -> int:
        return max(self.scale) if self.scale else 0


@dataclass(frozen=True)
class ExtractField:
    id: str
    question: str
    type: str


@dataclass(frozen=True)
class Criteria:
    name: str
    version: int | str
    context: str
    criteria: tuple[Criterion, ...]
    rules: tuple[Rule, ...]
    extract: tuple[ExtractField, ...] = ()
    hash: str = field(default="")

    @property
    def ref(self) -> str:
        return f"{self.name}@{self.version}"


def criteria_hash(data: dict[str, Any]) -> str:
    """sha256 of the canonical file, without `decision`.

    Rules are left out, so changing only the rules keeps the hash.
    Use `--redecide` to apply new rules without new LLM calls.
    """
    content = {k: v for k, v in data.items() if k != "decision"}
    canonical = json.dumps(content, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _check_id(value: Any, where: str, seen: set[str]) -> str:
    if not isinstance(value, str) or not _ID.match(value):
        raise CriteriaError(f"{where}.id: {value!r} must be snake_case")
    if value in seen:
        raise CriteriaError(f"{where}.id: {value!r} is used twice")
    seen.add(value)
    return value


def _check_question(item: dict[str, Any], where: str) -> str:
    question = item.get("question")
    if not isinstance(question, str) or not question.strip():
        raise CriteriaError(f"{where}.question: required")
    return " ".join(question.split())


def _parse_scale(raw: Any, where: str) -> dict[int, str]:
    if not isinstance(raw, dict) or not raw:
        raise CriteriaError(f"{where}.scale: a score needs a scale")
    keys = list(raw)
    if not all(isinstance(k, int) and not isinstance(k, bool) for k in keys):
        raise CriteriaError(f"{where}.scale: keys must be integers")
    if sorted(keys) != list(range(len(keys))):
        raise CriteriaError(f"{where}.scale: keys must be 0, 1, 2, ... with no gaps")
    return {k: str(raw[k]) for k in sorted(keys)}


def parse_criteria(data: Any) -> Criteria:
    if not isinstance(data, dict):
        raise CriteriaError("criteria file must be a mapping")
    for key in ("name", "version"):
        if key not in data:
            raise CriteriaError(f"{key}: required")

    raw_criteria = data.get("criteria")
    if not isinstance(raw_criteria, list) or not raw_criteria:
        raise CriteriaError("criteria: needs at least one criterion")
    seen: set[str] = set()
    criteria: list[Criterion] = []
    for i, item in enumerate(raw_criteria):
        where = f"criteria[{i}]"
        if not isinstance(item, dict):
            raise CriteriaError(f"{where}: must be a mapping")
        cid = _check_id(item.get("id"), where, seen)
        kind = item.get("type")
        if kind not in CRITERION_TYPES:
            raise CriteriaError(
                f"{where}.type: {kind!r} must be one of {', '.join(CRITERION_TYPES)}"
            )
        scale = _parse_scale(item.get("scale"), where) if kind == "score" else None
        criteria.append(Criterion(cid, _check_question(item, where), kind, scale))

    rules = _parse_rules(data.get("decision"), criteria)

    extract: list[ExtractField] = []
    for i, item in enumerate(data.get("extract") or []):
        where = f"extract[{i}]"
        if not isinstance(item, dict):
            raise CriteriaError(f"{where}: must be a mapping")
        eid = _check_id(item.get("id"), where, seen)
        kind = item.get("type")
        if kind not in EXTRACT_TYPES:
            raise CriteriaError(f"{where}.type: {kind!r} must be one of {', '.join(EXTRACT_TYPES)}")
        extract.append(ExtractField(eid, _check_question(item, where), kind))

    return Criteria(
        name=str(data["name"]),
        version=data["version"],
        context=str(data.get("context") or "").strip(),
        criteria=tuple(criteria),
        rules=tuple(rules),
        extract=tuple(extract),
        hash=criteria_hash(data),
    )


def _parse_rules(raw: Any, criteria: list[Criterion]) -> list[Rule]:
    if not isinstance(raw, list) or not raw:
        raise CriteriaError("decision: needs at least a default rule")
    types = {c.id: c.type for c in criteria}
    scales = {c.id: c.max_score for c in criteria if c.type == "score"}
    rules: list[Rule] = []
    for i, item in enumerate(raw):
        where = f"decision[{i}]"
        if not isinstance(item, dict):
            raise CriteriaError(f"{where}: must be a mapping")
        label = item.get("label")
        if label not in LABELS:
            raise CriteriaError(f"{where}.label: {label!r} must be one of {', '.join(LABELS)}")
        when = item.get("when")
        if when is None:
            if i != len(raw) - 1:
                raise CriteriaError(f"{where}: the default rule (no `when`) must come last")
            rules.append(Rule(label, ()))
            continue
        if isinstance(when, str):
            when = [when]
        if not isinstance(when, list) or not when:
            raise CriteriaError(f"{where}.when: must be a non-empty list of conditions")
        try:
            conditions = tuple(parse_condition(str(c), types, scales) for c in when)
        except RuleError as e:
            raise CriteriaError(f"{where}.when: {e}") from None
        rules.append(Rule(label, conditions))
    if rules[-1].conditions:
        raise CriteriaError("decision: the last rule must be a default rule with no `when`")
    return rules


def load_criteria(path: Path) -> Criteria:
    try:
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise CriteriaError(f"{path}: not valid YAML: {e}") from e
    try:
        return parse_criteria(data)
    except CriteriaError as e:
        raise CriteriaError(f"{path}: {e}") from None
