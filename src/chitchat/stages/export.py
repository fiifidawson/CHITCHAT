"""Stage 5: dataset.jsonl, dataset.csv, sources.json and the PRISMA report.

Only sanitized text is written. Raw text never leaves raw/.
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Any

from chitchat.config import PipelineConfig
from chitchat.ids import assign_tags
from chitchat.jsonl import read_json, read_jsonl, write_json, write_jsonl
from chitchat.prisma import check_totals, compute_prisma, render_markdown
from chitchat.run_dir import RunDir
from chitchat.screening.criteria import Criteria, load_criteria
from chitchat.screening.store import ScreeningStore
from chitchat.stages import StageError

log = logging.getLogger(__name__)

PAPER_FIELDS = (
    "title",
    "authors",
    "year",
    "doi",
    "url",
    "source",
    "search_category",
    "pdf_status",
    "abstract",
    "extracted_text",
    "privacy",
)
CSV_COLUMNS = (
    "tag",
    "paper_id",
    "title",
    "year",
    "doi",
    "url",
    "source",
    "pdf_status",
    "status",
    "label",
    "because",
)


def build_sources(papers: list[dict[str, Any]], docs: list[dict[str, Any]], labels: dict) -> dict:
    """`{tag: {kind, id, title, doi, url, year, label}}`. Tags have no personal data."""
    sources: dict[str, dict[str, Any]] = {}
    by_id = {p["paper_id"]: p for p in papers}
    for pid, tag in assign_tags(list(by_id), "P").items():
        p = by_id[pid]
        sources[tag] = {
            "kind": "paper",
            "id": pid,
            "title": p.get("title"),
            "doi": p.get("doi"),
            "url": p.get("url"),
            "year": p.get("year"),
            "label": labels.get(pid),
        }
    docs_by_id = {d["doc_id"]: d for d in docs}
    for did, tag in assign_tags(list(docs_by_id), "D").items():
        path = (docs_by_id[did].get("metadata") or {}).get("file_path") or ""
        sources[tag] = {"kind": "own_document", "id": did, "title": Path(path).name, "label": None}
    return sources


def dataset_rows(
    papers: list[dict[str, Any]], screening: dict[str, dict[str, Any]], tags: dict[str, str]
) -> list[dict[str, Any]]:
    rows = []
    for p in sorted(papers, key=lambda p: tags[p["paper_id"]]):
        record = screening.get(p["paper_id"]) or {}
        rows.append(
            {
                "tag": tags[p["paper_id"]],
                "paper_id": p["paper_id"],
                **{k: p.get(k) for k in PAPER_FIELDS},
                "screening": {
                    "status": record.get("status", "not_screened"),
                    "skip_reason": record.get("skip_reason"),
                    "decision": record.get("decision"),
                    "answers": record.get("answers"),
                    "extracted": record.get("extracted"),
                    "notes": record.get("notes"),
                    "provenance": record.get("provenance"),
                },
            }
        )
    return rows


def _cell(value: Any) -> Any:
    if isinstance(value, list):
        return "; ".join(str(v) for v in value)
    return "" if value is None else value


def write_csv(path: Path, rows: list[dict[str, Any]], criteria: Criteria) -> None:
    criterion_ids = [c.id for c in criteria.criteria]
    extract_ids = [f.id for f in criteria.extract]
    # utf-8-sig so Excel opens it correctly.
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([*CSV_COLUMNS, *criterion_ids, *extract_ids])
        for row in rows:
            s = row["screening"]
            decision = s["decision"] or {}
            answers = s["answers"] or {}
            extracted = s["extracted"] or {}
            writer.writerow(
                [
                    row["tag"],
                    row["paper_id"],
                    row["title"],
                    _cell(row["year"]),
                    _cell(row["doi"]),
                    _cell(row["url"]),
                    _cell(row["source"]),
                    _cell(row["pdf_status"]),
                    s["status"] if s["status"] != "skipped" else f"skipped: {s['skip_reason']}",
                    _cell(decision.get("label")),
                    "; ".join(decision.get("because") or []),
                    *[_cell((answers.get(cid) or {}).get("answer")) for cid in criterion_ids],
                    *[_cell((extracted.get(eid) or {}).get("answer")) for eid in extract_ids],
                ]
            )


def run_export(cfg: PipelineConfig, run: RunDir) -> dict[str, Any]:
    # A run can hold papers, your own documents, or both (documents only: no search).
    if not run.papers_sanitized.exists() and not run.docs_sanitized.exists():
        raise StageError(f"Nothing sanitized yet in {run.root}. Run the sanitize stage first.")
    criteria = load_criteria(cfg.screening.criteria)
    papers = list(read_jsonl(run.papers_sanitized)) if run.papers_sanitized.exists() else []
    docs = list(read_jsonl(run.docs_sanitized)) if run.docs_sanitized.exists() else []
    screening = ScreeningStore(run.screening).latest()
    labels = {pid: (r.get("decision") or {}).get("label") for pid, r in screening.items()}

    sources = build_sources(papers, docs, labels)
    write_json(run.sources, sources)
    tags = {s["id"]: tag for tag, s in sources.items()}

    rows = dataset_rows(papers, screening, tags)
    write_jsonl(run.dataset_jsonl, rows)
    write_csv(run.dataset_csv, rows, criteria)

    stats = read_json(run.discovery_stats) if run.discovery_stats.exists() else None
    prisma = compute_prisma(stats, papers, screening, len(docs), criteria)
    write_json(run.prisma_json, prisma)
    run.prisma_md.write_text(render_markdown(prisma), encoding="utf-8")

    for problem in check_totals(prisma):
        log.warning("PRISMA check: %s", problem)
    _print_summary(prisma, len(rows), run)
    return prisma


def _print_summary(prisma: dict[str, Any], n_rows: int, run: RunDir) -> None:
    from chitchat import ui

    included = prisma["included"]
    skipped = {k: v for k, v in prisma["excluded_before_screening"].items() if k != "total"}
    failed = {k: v for k, v in prisma["screening_failed"].items() if k != "total" and v}
    rows: list[ui.Fact] = [
        ("Papers", n_rows, "in the dataset"),
        (
            "Included",
            included["total"],
            ui.breakdown(included, ("HIGH", "MEDIUM", "LOW")),
            "bold green",
        ),
        ("Excluded", prisma["excluded_by_rules"]["total"], "by the decision rules", "bold red"),
        ("Skipped", prisma["excluded_before_screening"]["total"], ui.breakdown(skipped)),
    ]
    if prisma["screening_failed"]["total"]:
        rows.append(
            ("Failed", prisma["screening_failed"]["total"], ui.breakdown(failed), "bold magenta")
        )
    if prisma["not_screened_yet"]:
        rows.append(("Not screened", prisma["not_screened_yet"], "run the screen stage"))
    if prisma["own_documents_added"]:
        rows.append(("Own documents", prisma["own_documents_added"], "added"))
    ui.print_box(
        "Dataset and PRISMA",
        rows,
        footer=f"Saved to {ui.shorten_path(run.root)}: "
        "dataset.csv, dataset.jsonl, sources.json, prisma.md",
    )
