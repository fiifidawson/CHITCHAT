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


def status_rows(run: RunDir, stages: list[str]) -> list[tuple[str, str | None, str]]:
    """(stage, finished_at or None, what it produced) for each stage, then `ask`."""
    details = stage_details(run)
    return [(stage, run.done_at(stage), details.get(stage, "")) for stage in [*stages, "ask"]]


def last_runs(run: RunDir, n: int = 5) -> list[dict]:
    """The `n` most recent runs from history.jsonl, newest first."""
    if not run.history.exists():
        return []
    return list(read_jsonl(run.history))[-n:][::-1]


def stage_durations(run: RunDir) -> dict[str, float]:
    """How long each stage took the last time it finished."""
    durations: dict[str, float] = {}
    for record in last_runs(run, n=10_000)[::-1]:  # oldest first, so newer runs win
        for stage in record.get("stages", []):
            if stage.get("status") == "done":
                durations[stage["name"]] = stage["seconds"]
    return durations
