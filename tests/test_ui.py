from __future__ import annotations

from rich.console import Console

from chitchat import ui

LONG_TITLE = "A very long paper title " * 8


def _render(renderable, width: int = 80) -> str:
    console = Console(width=width, record=True, highlight=False, force_terminal=False)
    console.print(renderable)
    return console.export_text()


def _screened(label: str, because: list[str], content: str = "full_text") -> dict:
    return {
        "status": "screened",
        "title": LONG_TITLE,
        "decision": {"label": label, "because": because},
        "provenance": {"content": content, "usage": {"input_tokens": 100, "output_tokens": 10}},
    }


def test_full_title_is_shown_and_wrapped() -> None:
    text = _render(ui.paper_row(_screened("HIGH", ["humanity >= 2 (was 3)"])))
    assert " ".join(text.split()).startswith("HIGH " + " ".join(LONG_TITLE.split()))
    lines = text.splitlines()
    assert len(lines) > 2  # wrapped title plus the reason line
    assert all(line.startswith(" " * ui.BADGE_WIDTH) for line in lines[1:])  # hanging indent


def test_details() -> None:
    exclude = _screened("EXCLUDE", ["llm_data_collection == no (was no)"], content="abstract")
    assert ui.detail(exclude) == "rule: llm_data_collection == no · abstract only"
    high = _screened("HIGH", ["novel_methodology == yes (was yes)", "humanity >= 2 (was 3)"])
    assert ui.detail(high) == "matched: novel_methodology == yes; humanity >= 2 (was 3)"
    assert ui.detail(_screened("LOW", ["default"])) == ""

    old = {"status": "skipped", "skip_reason": "before_min_year", "metadata": {"year": 2015}}
    assert ui.detail(old, min_year=2020) == "published 2015, before 2020"
    assert ui.detail({"status": "skipped", "skip_reason": "no_text"}) == "no full text or abstract"
    error = {"status": "error", "error": "RateLimitError: slow down\nmore"}
    assert ui.detail(error) == "RateLimitError: slow down · retried next run"
    assert ui.badge(error) == "ERROR"


def test_summary() -> None:
    records = [
        _screened("HIGH", []),
        _screened("EXCLUDE", []),
        {"status": "skipped", "skip_reason": "no_text"},
        {"status": "error", "error": "x"},
    ]
    text = " ".join(_render(ui.summary_table(records, reused=5), width=100).split())
    assert "Included 1 HIGH 1 · MEDIUM 0 · LOW 0" in text
    assert "Excluded 1" in text
    assert "Skipped 1 no_text 1" in text
    assert "Failed 1 error 1 · retried next run" in text
    assert "Reused 5 from earlier runs" in text
    assert "200 in · 20 out" in text


def test_summary_panel() -> None:
    records = [_screened("HIGH", []), {"status": "skipped", "skip_reason": "no_text"}]
    panel = ui.summary_panel(records, reused=0, title="Screening done", footer="Saved to x.jsonl")
    assert panel.border_style == ui.ACCENT
    text = _render(panel, width=80)
    lines = text.strip().splitlines()
    assert "Screening done" in lines[0]  # title sits on the top border
    assert "Included" in text and "Saved to x.jsonl" in text
    assert all(len(line) == len(lines[0]) for line in lines)  # a closed box
