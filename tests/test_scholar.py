"""Google Scholar pacing, query shortening and the stop after a block. No network."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from chitchat.config import load_pipeline_config
from chitchat.stages.scholar import Pacer, ScholarBlocked, ScholarGate, scholar_query


class Clock:
    def __init__(self) -> None:
        self.now = 100.0
        self.slept: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


class Session:
    def __init__(self, *replies: tuple[int, str]) -> None:
        self.replies = list(replies)
        self.calls = 0

    def get(self, url: str, **kwargs) -> SimpleNamespace:
        self.calls += 1
        status, text = self.replies.pop(0)
        return SimpleNamespace(status_code=status, text=text)


def no_captcha(text: str) -> bool:
    return "captcha" in text


def test_pacer_waits_between_calls() -> None:
    clock = Clock()
    pacer = Pacer(10, clock=clock, sleep=clock.sleep)
    pacer.wait()
    clock.now += 4
    pacer.wait()
    assert clock.slept == [6]


def test_gate_stops_after_a_captcha() -> None:
    clock = Clock()
    gate = ScholarGate(Pacer(10, clock=clock, sleep=clock.sleep))
    session = Session((200, "results"), (200, "a captcha page"))
    assert gate.fetch(session, "u", no_captcha) == "results"
    with pytest.raises(ScholarBlocked):
        gate.fetch(session, "u", no_captcha)
    with pytest.raises(ScholarBlocked):
        gate.fetch(session, "u", no_captcha)
    assert session.calls == 2 and gate.stopped == "a captcha"


def test_gate_stops_on_an_error_status() -> None:
    clock = Clock()
    gate = ScholarGate(Pacer(10, clock=clock, sleep=clock.sleep))
    with pytest.raises(ScholarBlocked, match="429"):
        gate.fetch(Session((429, "")), "u", no_captcha)


def test_gate_stops_on_the_verification_redirect() -> None:
    clock = Clock()
    gate = ScholarGate(Pacer(10, clock=clock, sleep=clock.sleep))
    with pytest.raises(ScholarBlocked, match="verification"):
        gate.fetch(Session((302, "")), "u", no_captcha)


def test_long_query_keeps_the_first_terms() -> None:
    long = " AND ".join("(" + " OR ".join(f'"{c} term {i}"' for i in range(8)) + ")" for c in "abc")
    query = scholar_query(long, limit=120)
    assert len(query) <= 120
    assert query.startswith('("a term 0" OR "a term 1"')
    assert '"c term 0"' in query and " AND " not in query


def test_short_query_is_unchanged_but_for_and() -> None:
    assert scholar_query('("LLM" OR "GPT") AND ("consent")') == '("LLM" OR "GPT") ("consent")'


def test_rcp_config_runs_the_full_deep_search() -> None:
    repo = Path(__file__).resolve().parents[1]
    cfg = load_pipeline_config(repo / "configs" / "pipeline.rcp.yaml")
    deep = cfg.search.preset("deep")
    assert "google_scholar" in deep.sources
    assert (deep.max_categories, deep.max_results) == (6, 25)  # the defaults, not a short run
