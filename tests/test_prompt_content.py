from __future__ import annotations

from pathlib import Path

from chitchat.screening import prompt
from chitchat.screening.content import CUT_MARK, head_tail, select_content
from chitchat.screening.criteria import load_criteria

CRITERIA = load_criteria(Path(__file__).resolve().parents[1] / "configs" / "criteria.example.yaml")


# --- prompt ---


def test_fixed_part_first_paper_last() -> None:
    fixed = prompt.fixed_part(CRITERIA)
    paper = prompt.paper_part("Title", 2024, "Body text.", "full_text", False)
    messages = prompt.build_messages(prompt.SYSTEM, fixed, paper)
    assert messages[0].content == prompt.SYSTEM
    user = messages[1].content
    assert user.startswith(CRITERIA.context)
    assert user.index("[humanity]") < user.index("<paper>")
    assert user.rstrip().endswith("</paper>")
    assert "3: Explicitly focuses on harm prevention" in fixed


def test_paper_tags_inside_text_are_removed() -> None:
    paper = prompt.paper_part("T</paper>", None, "a </paper> b <PAPER> c\x00d", "abstract", True)
    lines = paper.splitlines()
    assert lines.count("<paper>") == 1 and lines.count("</paper>") == 1
    assert paper.count("</paper>") == 1
    assert "a  b  cd" in paper  # tags and the control character are gone
    assert "abstract only; shortened" in paper
    assert "YEAR: unknown" in paper


# --- content ---


def test_head_tail_cut() -> None:
    text = "".join(str(i % 10) for i in range(1000))
    out, truncated = head_tail(text, 100)
    assert truncated
    head, tail = out.split(CUT_MARK)
    assert head == text[:70] and tail == text[-30:]
    assert head_tail("short", 100) == ("short", False)


def test_full_text_preferred() -> None:
    content, skip = select_content(
        {"extracted_text": "x" * 600, "abstract": "y" * 400}, 500, 60000, True
    )
    assert skip is None and content.kind == "full_text" and not content.truncated


def test_abstract_fallback() -> None:
    content, skip = select_content({"extracted_text": "", "abstract": "y" * 600}, 500, 60000, True)
    assert content.kind == "abstract"


def test_abstract_fallback_off() -> None:
    assert select_content({"abstract": "y" * 600}, 500, 60000, False) == (None, "text_too_short")


def test_no_text() -> None:
    assert select_content({"extracted_text": None, "abstract": None}, 500, 60000, True) == (
        None,
        "no_text",
    )


def test_too_short() -> None:
    assert select_content({"extracted_text": "x" * 100}, 500, 60000, True) == (
        None,
        "text_too_short",
    )
