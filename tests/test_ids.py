from __future__ import annotations

from pathlib import Path

from chitchat.ids import doc_id, normalize_title, paper_id


def test_paper_id_uses_doi() -> None:
    assert paper_id({"doi": "10.1038/ABC", "title": "x"}) == "doi:10.1038/abc"


def test_paper_id_falls_back_to_title() -> None:
    a = paper_id({"doi": None, "title": "Data, Consent & LLMs!"})
    b = paper_id({"title": "data consent llms"})
    assert a == b
    assert a.startswith("title:") and len(a) == len("title:") + 16


def test_normalize_title() -> None:
    assert normalize_title("Hello, World 2!") == "helloworld2"


def test_doc_id_is_content_based(tmp_path: Path) -> None:
    a, b, c = tmp_path / "a.txt", tmp_path / "b.txt", tmp_path / "c.txt"
    a.write_text("same", encoding="utf-8")
    b.write_text("same", encoding="utf-8")
    c.write_text("other", encoding="utf-8")
    assert doc_id(a) == doc_id(b) != doc_id(c)
    assert doc_id(a).startswith("doc:")
