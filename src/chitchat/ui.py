"""Terminal output: one console, a screening progress bar, per-paper lines and a summary.

Colours and the live bar switch off by themselves when output is not a terminal.
"""

from __future__ import annotations

import io
import re
import sys
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from rich import box
from rich.console import Console, Group
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table
from rich.text import Text

console = Console(stderr=True, highlight=False)

ACCENT = "#f7cb46"  # mmore yellow, so our output matches its progress bars
BADGE_WIDTH = 9
STYLES = {
    "HIGH": "bold green",
    "MEDIUM": "green",
    "LOW": "yellow",
    "EXCLUDE": "red",
    "SKIPPED": "dim",
    "REFUSED": "magenta",
    "INVALID": "magenta",
    "ERROR": "bold red",
}
INCLUDED = ("HIGH", "MEDIUM", "LOW")
# "x == no (was no)" says the same thing twice; ordering conditions keep their value.
_EQUAL_WAS = re.compile(r"^(\S+ (?:==|!=) \S+) \(was [^)]*\)$")


class LateBoundStderr(io.TextIOBase):
    """Looks up sys.stderr on every write, so log lines appear above a live progress bar."""

    def write(self, text: str) -> int:
        return sys.stderr.write(text)

    def flush(self) -> None:
        sys.stderr.flush()


# --- One screening record --------------------------------------------------------


def badge(record: dict[str, Any]) -> str:
    """HIGH / MEDIUM / LOW / EXCLUDE for screened papers, else the status in capitals."""
    if record["status"] == "screened":
        return (record.get("decision") or {}).get("label") or "SCREENED"
    return record["status"].upper()


def detail(record: dict[str, Any], min_year: int | None = None) -> str:
    """Why the paper got its badge, in plain words."""
    status = record["status"]
    if status == "skipped":
        reason = record.get("skip_reason")
        year = (record.get("metadata") or {}).get("year")
        if reason == "before_min_year":
            return f"published {year}, before {min_year}" if min_year else f"published {year}"
        return {"no_text": "no full text or abstract", "text_too_short": "text too short"}.get(
            reason or "", reason or ""
        )
    if status in ("refused", "invalid", "error"):
        error = (record.get("error") or "").splitlines()[0] if record.get("error") else ""
        return f"{error[:120]} · retried next run" if error else "retried next run"
    because = (record.get("decision") or {}).get("because") or []
    conditions = [_EQUAL_WAS.sub(lambda m: m.group(1), c) for c in because if c != "default"]
    parts = [("rule: " if badge(record) == "EXCLUDE" else "matched: ") + "; ".join(conditions)]
    parts = parts if conditions else []
    if (record.get("provenance") or {}).get("content") == "abstract":
        parts.append("abstract only")
    return " · ".join(parts)


def paper_row(record: dict[str, Any], min_year: int | None = None) -> Table:
    """The coloured badge, then the full title with the reason on a dim second line."""
    label = badge(record)
    row = Table.grid(padding=(0, 1))
    row.add_column(width=BADGE_WIDTH, no_wrap=True)
    row.add_column(ratio=1, overflow="fold")
    body = Text(record.get("title") or "(no title)")
    reason = detail(record, min_year)
    if reason:
        body.append("\n" + reason, style="dim")
    row.add_row(Text(label, style=STYLES.get(label, "")), body)
    return row


# --- Whole run ---------------------------------------------------------------------


@contextmanager
def screening_progress(total: int, min_year: int | None = None) -> Iterator[Any]:
    """Yields `report(record)`: prints the paper's row and advances the bar."""
    progress = Progress(
        SpinnerColumn(style=ACCENT),
        TextColumn("Screening"),
        BarColumn(complete_style=ACCENT, finished_style=ACCENT, pulse_style=ACCENT),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        TextColumn("left"),
        TimeRemainingColumn(),
        console=console,
        transient=True,
    )
    with progress:
        task = progress.add_task("screen", total=total)

        def report(record: dict[str, Any]) -> None:
            progress.console.print(paper_row(record, min_year))
            progress.advance(task)

        yield report


def summary_table(records: list[dict[str, Any]], reused: int) -> Table:
    """Counts for this run's records, plus papers reused from earlier runs."""
    labels = Counter(badge(r) for r in records if r["status"] == "screened")
    skips = Counter(r.get("skip_reason") for r in records if r["status"] == "skipped")
    failed = Counter(r["status"] for r in records if r["status"] in ("refused", "invalid", "error"))
    tokens_in = sum(
        ((r.get("provenance") or {}).get("usage") or {}).get("input_tokens", 0) for r in records
    )
    tokens_out = sum(
        ((r.get("provenance") or {}).get("usage") or {}).get("output_tokens", 0) for r in records
    )

    def breakdown(counts: Counter[str], keys: tuple[str, ...] | None = None) -> str:
        items = [(k, counts[k]) for k in keys] if keys else sorted(counts.items())
        return " · ".join(f"{k} {v}" for k, v in items if v or keys)

    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold")
    table.add_column(justify="right")
    table.add_column(style="dim")
    table.add_row(
        Text("Included", style="bold green"),
        str(sum(labels[k] for k in INCLUDED)),
        breakdown(labels, INCLUDED),
    )
    table.add_row(Text("Excluded", style="bold red"), str(labels["EXCLUDE"]), "")
    table.add_row("Skipped", str(sum(skips.values())), breakdown(skips))
    if failed:
        table.add_row(
            Text("Failed", style="bold magenta"),
            str(sum(failed.values())),
            breakdown(failed) + " · retried next run",
        )
    if reused:
        table.add_row("Reused", str(reused), "from earlier runs")
    if tokens_in or tokens_out:
        table.add_row("Tokens", "", f"{tokens_in:,} in · {tokens_out:,} out")
    return table


def summary_panel(
    records: list[dict[str, Any]], reused: int, title: str, footer: str = ""
) -> Panel:
    """The summary table in a yellow box, with the title on the top border."""
    parts: list[Any] = [summary_table(records, reused)]
    if footer:
        parts += [Text(""), Text(footer, style="dim")]
    return Panel(
        Group(*parts),
        title=Text(f" {title} ", style=f"bold {ACCENT}"),
        title_align="left",
        border_style=ACCENT,
        box=box.ROUNDED,
        padding=(0, 1),
        expand=False,
    )


def print_summary(records: list[dict[str, Any]], reused: int, title: str, footer: str = "") -> None:
    console.print()
    console.print(summary_panel(records, reused, title, footer))
