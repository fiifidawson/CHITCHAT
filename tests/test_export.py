from __future__ import annotations

import csv
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from chitchat.ids import assign_tags
from chitchat.jsonl import read_json, read_jsonl, write_json, write_jsonl
from chitchat.prisma import check_totals
from chitchat.run_dir import RunDir
from chitchat.screening.criteria import load_criteria
from chitchat.stages import StageError
from chitchat.stages.export import CSV_COLUMNS, run_export

REPO = Path(__file__).resolve().parents[1]
CRITERIA_PATH = REPO / "configs" / "criteria.example.yaml"
CRITERIA = load_criteria(CRITERIA_PATH)
RAW_SECRET = "Alice Smith"


def _paper(n: int, pdf: str = "downloaded") -> dict[str, Any]:
    return {
        "paper_id": f"doi:10.1/{n}",
        "title": f"Paper {n}",
        "authors": ["[PERSON_1]"],
        "year": 2024,
        "doi": f"10.1/{n}",
        "url": f"https://x/{n}",
        "source": "openalex" if n % 2 else "arxiv",
        "pdf_status": pdf,
        "abstract": "Sanitized abstract by [PERSON_1].",
        "extracted_text": "Sanitized text.",
        "privacy": {"count": 1, "entities": {"PERSON": 1}, "level": "low"},
    }


def _record(n: int, status: str, **extra: Any) -> dict[str, Any]:
    prov = {"criteria_hash": CRITERIA.hash, "model": "m", "content": extra.pop("content", None)}
    return {"paper_id": f"doi:10.1/{n}", "title": f"Paper {n}", "status": status,
            "provenance": prov, **extra}  # fmt: skip


def _screened(n: int, label: str, rule_index: int, content: str = "full_text") -> dict[str, Any]:
    answers = {c.id: {"answer": 2 if c.type == "score" else "yes", "evidence": "q"}
               for c in CRITERIA.criteria}  # fmt: skip
    extracted = {"datasets": {"answer": ["A", "B"], "evidence": "q"}}
    decision = {"label": label, "rule_index": rule_index, "because": ["x == yes (was yes)"]}
    return _record(n, "screened", decision=decision, answers=answers, extracted=extracted,
                   content=content)  # fmt: skip


@pytest.fixture
def run(tmp_path: Path) -> tuple[Any, RunDir]:
    """10 papers: 2 skipped, 1 failed, 1 not screened, 6 screened (2 excluded, 4 included)."""
    rd = RunDir(tmp_path / "runs" / "t")
    papers = [_paper(n, "refused" if n in (2, 3) else "downloaded") for n in range(1, 11)]
    write_jsonl(rd.papers_sanitized, papers)
    write_jsonl(rd.papers_raw, [{**p, "extracted_text": RAW_SECRET} for p in papers])
    write_json(
        rd.discovery_stats,
        {"found": {"openalex": 7, "arxiv": 5}, "n_unique": 10,
         "pdf_counts": {"downloaded": 8, "refused": 2}},
    )  # fmt: skip
    records = [
        _record(1, "skipped", skip_reason="before_min_year"),
        _record(2, "skipped", skip_reason="no_text"),
        _record(3, "error", error="boom"),
        _screened(4, "EXCLUDE", 0),
        _screened(5, "EXCLUDE", 0),
        _screened(6, "HIGH", 3),
        _screened(7, "HIGH", 3),
        _screened(8, "MEDIUM", 4, content="abstract"),
        _screened(9, "LOW", 7),
        # paper 10: not screened yet
    ]
    write_jsonl(rd.screening, records)
    write_jsonl(
        rd.docs_sanitized,
        [{"doc_id": "doc:abc", "text": "t", "metadata": {"file_path": "/x/notes.pdf"}}],
    )
    cfg = SimpleNamespace(screening=SimpleNamespace(criteria=CRITERIA_PATH))
    return cfg, rd


def test_prisma_numbers_add_up(run) -> None:
    cfg, rd = run
    p = run_export(cfg, rd)
    assert p["identified"] == {"per_source": {"openalex": 7, "arxiv": 5}, "total": 12}
    assert p["duplicates_removed"] == 2
    assert p["records_after_dedupe"] == 10
    assert p["full_text"] == {"obtained": 8, "not_obtained": {"refused": 2}}
    assert p["excluded_before_screening"] == {"total": 2, "before_min_year": 1, "no_text": 1}
    assert p["screening_failed"] == {"total": 1, "refused": 0, "invalid": 0, "error": 1}
    assert p["not_screened_yet"] == 1
    assert p["screened"] == {"total": 6, "full_text": 5, "abstract_only": 1}
    assert p["excluded_by_rules"]["total"] == 2
    assert p["excluded_by_rules"]["rule 0: llm_data_collection == no"] == 2
    assert p["included"] == {"total": 4, "HIGH": 2, "MEDIUM": 1, "LOW": 1}
    assert p["own_documents_added"] == 1
    assert check_totals(p) == []
    assert read_json(rd.prisma_json) == p
    md = rd.prisma_md.read_text(encoding="utf-8")
    assert "Records identified: **12**" in md and "```mermaid" in md


def test_dataset_and_csv(run) -> None:
    cfg, rd = run
    run_export(cfg, rd)
    rows = list(read_jsonl(rd.dataset_jsonl))
    assert [r["tag"] for r in rows] == sorted(r["tag"] for r in rows)
    assert len(rows) == 10
    assert rows[0]["screening"]["status"] in {"skipped", "screened", "error", "not_screened"}
    assert RAW_SECRET not in rd.dataset_jsonl.read_text(encoding="utf-8")

    raw = rd.dataset_csv.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")  # utf-8-sig for Excel
    with open(rd.dataset_csv, encoding="utf-8-sig", newline="") as f:
        table = list(csv.DictReader(f))
    header = list(table[0])
    criteria_ids = [c.id for c in CRITERIA.criteria]
    extract_ids = [e.id for e in CRITERIA.extract]
    assert header == [*CSV_COLUMNS, *criteria_ids, *extract_ids]
    high = next(r for r in table if r["paper_id"] == "doi:10.1/6")
    assert high["label"] == "HIGH" and high["humanity"] == "2" and high["datasets"] == "A; B"
    assert next(r for r in table if r["paper_id"] == "doi:10.1/1")["status"] == (
        "skipped: before_min_year"
    )
    assert next(r for r in table if r["paper_id"] == "doi:10.1/10")["status"] == "not_screened"


def test_sources_json(run) -> None:
    cfg, rd = run
    run_export(cfg, rd)
    sources = read_json(rd.sources)
    assert sources["D0001"] == {"kind": "own_document", "id": "doc:abc", "title": "notes.pdf",
                                "label": None}  # fmt: skip
    papers = {t: s for t, s in sources.items() if t.startswith("P")}
    assert len(papers) == 10
    assert all(s["kind"] == "paper" for s in papers.values())


def test_tags_are_stable() -> None:
    ids = ["doi:b", "doi:a", "title:c"]
    assert assign_tags(ids, "P") == assign_tags(list(reversed(ids)), "P")
    assert assign_tags(ids, "P") == {"doi:a": "P0001", "doi:b": "P0002", "title:c": "P0003"}


def test_check_totals_flags_mismatch(run) -> None:
    cfg, rd = run
    p = run_export(cfg, rd)
    p["records_after_dedupe"] += 1
    assert check_totals(p)


def test_needs_sanitized_papers(tmp_path: Path) -> None:
    cfg = SimpleNamespace(screening=SimpleNamespace(criteria=CRITERIA_PATH))
    with pytest.raises(StageError, match="sanitize"):
        run_export(cfg, RunDir(tmp_path))
