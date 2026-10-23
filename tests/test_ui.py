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


def test_queries_table_flags_long_queries() -> None:
    queries = [
        {"category": "Short", "query": "(a) AND (b)"},
        {"category": "Long", "query": "x" * 20},
    ]
    text = _render(ui.queries_table(queries, openalex_limit=15), width=100)
    assert "Boolean queries" in text
    short = next(line for line in text.splitlines() if "Short" in line)
    long = next(line for line in text.splitlines() if "Long" in line)
    assert "ok" in short and " 2 " in short  # two AND groups
    assert "too long" in long
    assert "OpenAlex" not in _render(ui.queries_table(queries, openalex_limit=None), width=100)


def test_status_table(tmp_path) -> None:
    rows = [("discover", "2026-10-14T19:52:00+00:00", "15 papers"), ("index", None, "")]
    text = _render(ui.status_table(rows, tmp_path), width=100)
    discover = next(line for line in text.splitlines() if "discover" in line)
    assert "✓" in discover and "2026-10-14 19:52" in discover and "15 papers" in discover
    assert "–" in next(line for line in text.splitlines() if "index" in line)


def test_answer_view() -> None:
    result = {
        "question": "Who is Sarah?",
        "answer": "It is [PERSON_1] [P0001].",
        "aborted": False,
        "sources": [{"tag": "P0001", "title": "A", "year": 2024, "doi": "10.1/a", "known": True}],
        "retrieved": [],
        "privacy_report_summary": {
            "outcome": "returned",
            "sanitized_query": "Who is [PERSON_1]?",
            "question_masked": 1,
            "question_entities": {"PERSON": 1},
            "spans_masked": 0,
            "entities": {},
        },
    }
    text = _render(ui.answer_view(result), width=100)
    assert "Answer" in text.splitlines()[0]  # boxed, title on the border
    assert "[P0001] A (2024)" in text and "https://doi.org/10.1/a" in text
    assert "Privacy mode sent your question as: Who is [PERSON_1]?" in text
    assert "question: 1 masked (PERSON 1) · context: nothing masked" in text


def test_log_handler_styles_warnings(monkeypatch) -> None:
    import logging

    console = Console(width=100, record=True, force_terminal=False)
    monkeypatch.setattr(ui, "console", console)
    logger = logging.getLogger("chitchat.test_ui")
    logger.addHandler(ui.ConsoleLogHandler())
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.info("plain info")
    logger.warning("watch out")
    text = console.export_text()
    assert "plain info" in text and "⚠ watch out" in text


def test_queries_table_shows_concepts() -> None:
    queries = [{"category": "Consent", "concepts": ["consent", "LLMs"], "query": "(a) AND (b)"}]
    text = _render(ui.queries_table(queries, openalex_limit=1500), width=120)
    assert "Concepts (all must match)" in text and "consent AND LLMs" in text


def test_draft_view_partitions_categories() -> None:
    categories = [
        ("Consent in data", [("consent", ["opt-out"]), ("data", ["datasets"])], 120),
        ("Too broad", [("x" * 10, [])], 2000),
    ]
    text = _render(ui.draft_view(categories, limit=1500), width=100)
    assert "Draft search: 2 categories · 3 concepts · 1/2 fit OpenAlex" in text
    first, second = text.split("Category 2 · Too broad")
    assert "Category 1 · Consent in data" in first and "or: opt-out" in first and "AND" in first
    assert "120 characters · OpenAlex ok" in first
    assert "(no synonyms)" in second and "too long" in second
