"""`chitchat status`: what each stage has produced so far."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from chitchat.jsonl import read_json, read_jsonl
from chitchat.run_dir import RunDir
from chitchat.screening.store import ScreeningStore


def _count(path: Path) -> int | None:
    return sum(1 for _ in read_jsonl(path)) if path.exists() else None


def _plural(n: int, word: str, plural: str = "") -> str:
    return f"{n} {word if n == 1 else plural or word + 's'}"


def stage_details(run: RunDir) -> dict[str, str]:
    """One short line per stage that has output."""
    details: dict[str, str] = {}

    if run.queries.exists():
        details["queries"] = _plural(len(read_json(run.queries)), "query", "queries")
    if run.discovery_stats.exists():
        stats = read_json(run.discovery_stats)
        pdfs = sum(stats["pdf_counts"].get(s, 0) for s in ("downloaded", "cached"))
        details["discover"] = f"{_plural(stats['n_unique'], 'paper')}, {pdfs} with PDF"
    if (n := _count(run.docs_raw)) is not None:
        details["ingest"] = _plural(n, "own document")
    if run.privacy_report.exists():
        report = read_json(run.privacy_report)
        parts = [f"{k.replace('_', ' ')}: {v['spans']} spans masked" for k, v in report.items()]
        details["sanitize"] = "; ".join(parts) or "nothing sanitized"
    records = ScreeningStore(run.screening).latest()
    if records:
        statuses = Counter(r["status"] for r in records.values())
        labels = Counter(
            (r.get("decision") or {}).get("label")
            for r in records.values()
            if r["status"] == "screened"
        )
        label_text = ", ".join(f"{k} {labels[k]}" for k in ("HIGH", "MEDIUM", "LOW", "EXCLUDE"))
        details["screen"] = ", ".join(f"{k} {v}" for k, v in sorted(statuses.items()))
        details["screen"] += f" ({label_text})"
    if run.prisma_json.exists():
        included = read_json(run.prisma_json)["included"]["total"]
        details["export"] = f"{_count(run.dataset_jsonl) or 0} rows, {included} included"
    if (n := _count(run.chunks)) is not None:
        details["index"] = _plural(n, "chunk")
    if (n := _count(run.answers)) is not None:
        details["ask"] = _plural(n, "answer")
    return details


def render_status(run: RunDir, stages: list[str]) -> str:
    details = stage_details(run)
    lines = [f"Run folder: {run.root}", ""]
    width = max(len(s) for s in [*stages, "ask"])
    for stage in [*stages, "ask"]:
        done = run.done_at(stage)
        mark = "done" if done or (stage == "ask" and stage in details) else "-"
        when = f" ({done[:16].replace('T', ' ')} UTC)" if done else ""
        detail = details.get(stage, "")
        lines.append(f"  {stage:<{width}}  {mark:<4}{when}  {detail}".rstrip())
    return "\n".join(lines)
