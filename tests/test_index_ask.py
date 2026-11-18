from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from chitchat.ask import CITE_RULES, NO_ANSWER, cited_tags, format_result, render
from chitchat.stages.index import prefix_tag, select_items

REPO = Path(__file__).resolve().parents[1]

SOURCES = {
    "P0001": {"kind": "paper", "id": "doi:10.1/a", "title": "A", "doi": "10.1/a", "year": 2024},
    "P0002": {"kind": "paper", "id": "doi:10.1/b", "title": "B", "doi": None, "url": "https://b"},
    "P0003": {"kind": "paper", "id": "doi:10.1/c", "title": "C"},
    "D0001": {"kind": "own_document", "id": "doc:x", "title": "notes.pdf"},
}


def _screened(label: str) -> dict:
    return {"status": "screened", "decision": {"label": label}}


# --- index ---------------------------------------------------------------------


def test_select_items() -> None:
    papers = [
        {"paper_id": "doi:10.1/a", "title": "A", "extracted_text": "Full A.", "abstract": "Abs A"},
        {"paper_id": "doi:10.1/b", "title": "B", "extracted_text": "", "abstract": "Abs B"},
        {"paper_id": "doi:10.1/c", "title": "C", "extracted_text": "Full C."},
    ]
    screening = {"doi:10.1/a": _screened("HIGH"), "doi:10.1/b": _screened("LOW"),
                 "doi:10.1/c": _screened("EXCLUDE")}  # fmt: skip
    docs = [{"doc_id": "doc:x", "text": "My notes."}]

    items = select_items(papers, screening, docs, SOURCES, ["HIGH", "LOW"], True)
    assert [(i["tag"], i["text"]) for i in items] == [
        ("P0001", "Full A."),
        ("P0002", "Abs B"),  # no full text: abstract
        ("D0001", "My notes."),
    ]
    assert items[0]["extra"]["label"] == "HIGH"

    only_high = select_items(papers, screening, docs, SOURCES, ["HIGH"], False)
    assert [i["tag"] for i in only_high] == ["P0001"]


def test_prefix_tag() -> None:
    assert prefix_tag("Some text.", "P0007") == "[P0007] Some text."


# --- ask -------------------------------------------------------------------------


class Outcome(StrEnum):  # mirrors mmore's ReportOutcome
    RETURNED = "returned"
    ABORTED_UNSAFE = "aborted-unsafe"


def _doc(tag: str) -> SimpleNamespace:
    return SimpleNamespace(page_content=f"[{tag}] text", metadata={"file_path": tag, "rank": 1})


def test_cited_tags_in_order() -> None:
    assert cited_tags("See [P0002] and [D0001], also [P0002] and [X1].") == ["P0002", "D0001"]


def test_tags_map_to_sources() -> None:
    out = {"answer": "Consent is opt-out [P0002][P0001]. Also [P0099].",
           "docs": [_doc("P0001"), _doc("P0002"), _doc("P0001")]}  # fmt: skip
    result = format_result("q?", out, SOURCES)
    assert [s["tag"] for s in result["sources"]] == ["P0002", "P0001", "P0099"]
    assert result["sources"][1]["doi"] == "10.1/a"
    assert result["sources"][2]["known"] is False
    assert [s["tag"] for s in result["retrieved"]] == ["P0001", "P0002"]
    assert result["privacy_report_summary"] is None
    text = render(result)
    assert "[P0001] A (2024) https://doi.org/10.1/a" in text
    assert "[P0002] B https://b" in text
    assert "(unknown tag)" in text
    json.dumps(result)


def test_retrieved_docs_as_dicts() -> None:
    """mmore's output passes through model_dump(), so docs arrive as dicts."""
    docs = [{"page_content": "[P0002] x", "metadata": {"file_path": "P0002", "rank": 1}}]
    result = format_result("q?", {"answer": "No.", "docs": docs}, SOURCES)
    assert [s["tag"] for s in result["retrieved"]] == ["P0002"]


def test_aborted_unsafe_is_handled() -> None:
    report = {"outcome": Outcome.ABORTED_UNSAFE, "gate_outcome": "aborted",
              "detection": {"count": 3, "entity_counts": {"PERSON": 3}}}  # fmt: skip
    result = format_result("q?", {"answer": "", "docs": [], "privacy_report": report}, SOURCES)
    assert result["aborted"] is True
    assert result["answer"] == NO_ANSWER
    assert result["sources"] == []
    assert result["privacy_report_summary"]["outcome"] == "aborted-unsafe"
    assert "aborted-unsafe · question: nothing masked · context: 3 masked (PERSON 3)" in render(
        result
    )
    json.dumps(result)


def test_masked_question_is_shown() -> None:
    report = {"outcome": Outcome.RETURNED, "sanitized_query": "who is [PERSON_1]?",
              "detection": {"count": 1, "entity_counts": {"PERSON": 1}}}  # fmt: skip
    result = format_result("q?", {"answer": "Yes [P0001].", "privacy_report": report}, SOURCES)
    summary = result["privacy_report_summary"]
    assert summary["outcome"] == "returned"
    assert summary["sanitized_query"] == "who is [PERSON_1]?"
    assert "privacy mode sent your question as: who is [PERSON_1]?" in render(result)


def test_privacy_config_gets_citation_rules() -> None:
    pytest.importorskip("mmore.privacy")
    from chitchat.ask import _privacy_config

    default = {"llm_name": "qwen3.5:9b", "base_url": "http://localhost:11434/v1"}
    cfg = _privacy_config(str(REPO / "configs" / "rag_privacy.yaml"), False, default)
    assert CITE_RULES in cfg.answer.system_prompt
    assert cfg.interactive is False
    # No answer.llm in rag_privacy.yaml: privacy mode answers with the pipeline's model.
    assert cfg.answer.llm.llm_name == "qwen3.5:9b"


def test_privacy_config_answer_llm_wins(tmp_path: Path) -> None:
    pytest.importorskip("mmore.privacy")
    from chitchat.ask import _privacy_config

    data = yaml.safe_load((REPO / "configs" / "rag_privacy.yaml").read_text(encoding="utf-8"))
    data["answer"] = {"llm": {"llm_name": "other-model", "base_url": "http://x/v1"}}
    path = tmp_path / "p.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    cfg = _privacy_config(str(path), False, {"llm_name": "qwen3.5:9b"})
    assert cfg.answer.llm.llm_name == "other-model"


def test_privacy_config_needs_answer_llm(tmp_path: Path) -> None:
    pytest.importorskip("mmore.privacy")
    from chitchat.ask import _privacy_config
    from chitchat.stages import StageError

    data = yaml.safe_load((REPO / "configs" / "rag_privacy.yaml").read_text(encoding="utf-8"))
    data.pop("answer", None)
    path = tmp_path / "p.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(StageError, match="answer.llm"):
        _privacy_config(str(path), review=False)


@pytest.mark.slow
def test_presidio_leaves_tags_alone() -> None:
    """If this fails, change the tag format to [SRC-0007]."""
    from chitchat.stages.sanitize import Sanitizer, load_sanitize_configs

    configs = load_sanitize_configs(REPO / "configs" / "sanitize.yaml")
    sanitizer = Sanitizer.from_dict(configs["own_documents"])
    text = "[P0007] John Smith said consent matters. [D0012] See also [P0130]."
    (clean,), report = sanitizer.sanitize([text])
    assert "[P0007]" in clean and "[D0012]" in clean and "[P0130]" in clean
    assert "John Smith" not in clean


def test_question_masks_are_counted() -> None:
    """The context count alone said "0 masked" even when the question was masked."""
    report = {"outcome": Outcome.RETURNED,
              "sanitized_query": "I'm [PERSON_1] ([EMAIL_ADDRESS_1], [PHONE_NUMBER_1]). Gaps?",
              "detection": {"count": 0, "entity_counts": {}}}  # fmt: skip
    summary = format_result("q?", {"answer": "x", "privacy_report": report}, SOURCES)[
        "privacy_report_summary"
    ]
    assert summary["question_masked"] == 3
    assert summary["question_entities"] == {"PERSON": 1, "EMAIL_ADDRESS": 1, "PHONE_NUMBER": 1}
    text = render(format_result("q?", {"answer": "x", "privacy_report": report}, SOURCES))
    assert "question: 3 masked (PERSON 1, EMAIL_ADDRESS 1, PHONE_NUMBER 1)" in text
    assert "context: nothing masked" in text


def test_uncited_answer_lists_retrieved_sources() -> None:
    out = {"answer": "Written by [PERSON_2]. Contact: [EMAIL_ADDRESS_1].",
           "docs": [_doc("P0001"), _doc("P0001")]}  # fmt: skip
    text = render(format_result("q?", out, SOURCES))
    assert "Sources (retrieved, not cited by the model):" in text
    assert "[P0001] A (2024) https://doi.org/10.1/a" in text
    assert "[PERSON_2]" in text  # masked tokens are not mistaken for tags
    assert format_result("q?", out, SOURCES)["sources"] == []


def test_nothing_retrieved() -> None:
    text = render(format_result("q?", {"answer": "No idea.", "docs": []}, SOURCES))
    assert "No sources: nothing was retrieved." in text
