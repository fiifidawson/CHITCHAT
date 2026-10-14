from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from chitchat.screening.criteria import CriteriaError, load_criteria, parse_criteria

REPO = Path(__file__).resolve().parents[1]
EXAMPLE = REPO / "configs" / "criteria.example.yaml"

BASE = {
    "name": "t",
    "version": 1,
    "context": "ctx",
    "criteria": [
        {"id": "in_scope", "question": "In scope?", "type": "yes_no"},
        {
            "id": "quality",
            "question": "Quality?",
            "type": "score",
            "scale": {0: "low", 1: "mid", 2: "high"},
        },
        {"id": "summary", "question": "Summary?", "type": "text"},
    ],
    "decision": [
        {"label": "EXCLUDE", "when": ["in_scope == no"]},
        {"label": "HIGH", "when": ["quality >= 2"]},
        {"label": "LOW"},
    ],
    "extract": [{"id": "datasets", "question": "Datasets?", "type": "list"}],
}


def _with(**changes):
    data = copy.deepcopy(BASE)
    data.update(changes)
    return data


def test_example_file_is_valid() -> None:
    c = load_criteria(EXAMPLE)
    assert c.ref == "humanitarian-llm-data@1"
    assert len(c.criteria) == 17
    assert c.rules[-1].conditions == ()
    assert [f.id for f in c.extract] == [
        "datasets",
        "data_sources",
        "languages",
        "consent_approach",
    ]


def test_base_is_valid() -> None:
    c = parse_criteria(BASE)
    assert [x.id for x in c.criteria] == ["in_scope", "quality", "summary"]
    assert c.criteria[1].max_score == 2


@pytest.mark.parametrize(
    ("data", "match"),
    [
        ({k: v for k, v in BASE.items() if k != "name"}, "name"),
        (_with(criteria=[]), "criteria"),
        (_with(criteria=[{"id": "Bad-Id", "question": "q", "type": "yes_no"}]), "snake_case"),
        (_with(criteria=[BASE["criteria"][0], BASE["criteria"][0]]), "used twice"),
        (_with(criteria=[{"id": "a", "question": "q", "type": "maybe"}]), r"criteria\[0\]\.type"),
        (_with(criteria=[{"id": "a", "question": "", "type": "yes_no"}]), "question"),
        (_with(criteria=[{"id": "a", "question": "q", "type": "score"}]), "needs a scale"),
        (
            _with(
                criteria=[{"id": "a", "question": "q", "type": "score", "scale": {1: "x", 2: "y"}}]
            ),
            "no gaps",
        ),
        (
            _with(decision=[{"label": "LOW", "when": ["nope == yes"]}, {"label": "LOW"}]),
            "unknown criterion",
        ),
        (
            _with(decision=[{"label": "LOW", "when": ["in_scope == 3"]}, {"label": "LOW"}]),
            "yes, no or unclear",
        ),
        (
            _with(decision=[{"label": "LOW", "when": ["in_scope >= yes"]}, {"label": "LOW"}]),
            "== or !=",
        ),
        (_with(decision=[{"label": "LOW", "when": ["quality >= 5"]}, {"label": "LOW"}]), r"0\.\.2"),
        (
            _with(decision=[{"label": "LOW", "when": ["summary == x"]}, {"label": "LOW"}]),
            "can't be used",
        ),
        (
            _with(decision=[{"label": "LOW", "when": ["quality >> 1"]}, {"label": "LOW"}]),
            "can't read",
        ),
        (
            _with(decision=[{"label": "LOW"}, {"label": "HIGH", "when": ["quality >= 1"]}]),
            "must come last",
        ),
        (_with(decision=[{"label": "HIGH", "when": ["quality >= 1"]}]), "default rule"),
        (_with(decision=[{"label": "MAYBE"}]), "label"),
        (_with(extract=[{"id": "x", "question": "q", "type": "date"}]), r"extract\[0\]\.type"),
        (_with(extract=[{"id": "in_scope", "question": "q", "type": "list"}]), "used twice"),
    ],
)
def test_validation_errors(data, match) -> None:
    with pytest.raises(CriteriaError, match=match):
        parse_criteria(data)


def test_hash_is_stable_and_ignores_rules() -> None:
    a = parse_criteria(BASE).hash
    assert a == parse_criteria(copy.deepcopy(BASE)).hash
    assert a.startswith("sha256:")
    changed_rules = _with(decision=[{"label": "MEDIUM"}])
    assert parse_criteria(changed_rules).hash == a
    changed_question = copy.deepcopy(BASE)
    changed_question["criteria"][0]["question"] = "Different?"
    assert parse_criteria(changed_question).hash != a


def test_load_names_the_file(tmp_path: Path) -> None:
    path = tmp_path / "c.yaml"
    path.write_text(yaml.safe_dump(_with(criteria=[])), encoding="utf-8")
    with pytest.raises(CriteriaError, match="c.yaml"):
        load_criteria(path)
