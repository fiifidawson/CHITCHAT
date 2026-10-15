"""Terminal output for every command: stage headers, progress bars, summary boxes and tables.

One console, on stderr. Colours and live bars switch off by themselves when output
is not a terminal (a log file, CI), and everything stays readable as plain text.
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from rich import box
from rich.console import Console, Group, RenderableType
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

console = Console(stderr=True, highlight=False)  # progress, logs, stage summaries
out = Console(highlight=False)  # results you may want to pipe or save: answers, status

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

# (label, value, detail[, label style]) rows for a summary box.
Fact = tuple[Any, ...]


# --- Building blocks ------------------------------------------------------------------


class ConsoleLogHandler(logging.Handler):
    """Log lines through the console: dim info, yellow warnings, red errors.

    Using the console keeps log lines above a live progress bar instead of breaking it.
    """

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = self.format(record)
            if record.levelno >= logging.ERROR:
                console.print(Text(f"✗ {message}", style="bold red"))
            elif record.levelno >= logging.WARNING:
                console.print(Text(f"⚠ {message}", style=ACCENT))
            else:
                console.print(Text(message, style="dim"))
        except Exception:  # noqa: BLE001
            self.handleError(record)


def stage_header(name: str, position: int, total: int) -> None:
    console.print()
    console.rule(
        Text(f" {name} · {position}/{total} ", style=f"bold {ACCENT}"), style=ACCENT, align="left"
    )


def note(message: str) -> None:
    """A quiet one-line message."""
    console.print(Text(message, style="dim"))


def facts(rows: list[Fact]) -> Table:
    """Label, value and a dim detail per row, aligned."""
    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold")
    table.add_column(justify="right")
    table.add_column(style="dim", overflow="fold")
    for row in rows:
        label, value, detail_text = row[0], row[1], row[2] if len(row) > 2 else ""
        style = row[3] if len(row) > 3 else ""
        table.add_row(Text(str(label), style=style or "bold"), str(value), str(detail_text or ""))
    return table


def boxed(title: str, body: RenderableType, footer: str | list[str] = "") -> Panel:
    """A yellow box, with the title on the top border and dim footer lines."""
    parts: list[Any] = [body]
    lines = [footer] if isinstance(footer, str) else footer
    if any(lines):
        parts.append(Text(""))
        parts += [Text(line, style="dim") for line in lines if line]
    return Panel(
        Group(*parts),
        title=Text(f" {title} ", style=f"bold {ACCENT}"),
        title_align="left",
        border_style=ACCENT,
        box=box.ROUNDED,
        padding=(0, 1),
        expand=False,
    )


def print_box(title: str, rows: list[Fact], footer: str | list[str] = "") -> None:
    console.print(boxed(title, facts(rows), footer))


def breakdown(counts: dict[str, int] | Counter[str], keys: tuple[str, ...] | None = None) -> str:
    """`a 2 · b 1`. With `keys`, keeps that order and shows zeros."""
    items = [(k, counts.get(k, 0)) for k in keys] if keys else sorted(counts.items())
    return " · ".join(f"{k} {v}" for k, v in items if v or keys)


def _bar(label: str) -> Progress:
    return Progress(
        SpinnerColumn(style=ACCENT),
        TextColumn(label),
        BarColumn(complete_style=ACCENT, finished_style=ACCENT, pulse_style=ACCENT),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        TextColumn("left"),
        TimeRemainingColumn(),
        console=console,
        transient=True,
    )


@contextmanager
def progress(label: str, total: int) -> Iterator[Callable[[], None]]:
    """Yields `advance()`. The bar disappears when done."""
    bar = _bar(label)
    with bar:
        task = bar.add_task(label, total=total)
        yield lambda: bar.advance(task)


def shorten_path(path: Path | str) -> str:
    """The path relative to the working folder when possible: shorter to read."""
    try:
        return str(Path(path).resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path)


# --- Queries ---------------------------------------------------------------------------


def queries_table(queries: list[dict[str, str]], openalex_limit: int | None) -> Table:
    """One row per category. With `openalex_limit`, flags queries OpenAlex will reject."""
    table = Table(
        title=Text("Boolean queries", style=f"bold {ACCENT}"),
        title_justify="left",
        box=box.ROUNDED,
        border_style=ACCENT,
        header_style="bold",
    )
    table.add_column("#", justify="right", style="dim")
    table.add_column("Category")
    table.add_column("AND groups", justify="right")
    table.add_column("Characters", justify="right")
    if openalex_limit:
        table.add_column("OpenAlex")
    for n, q in enumerate(queries, 1):
        length = len(q["query"])
        row = [str(n), q["category"], str(q["query"].count(" AND ") + 1), f"{length:,}"]
        if openalex_limit:
            row.append("[green]ok[/]" if length <= openalex_limit else "[red]too long[/]")
        table.add_row(*row)
    return table


# --- Screening ------------------------------------------------------------------------


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


@contextmanager
def screening_progress(total: int, min_year: int | None = None) -> Iterator[Any]:
    """Yields `report(record)`: prints the paper's row and advances the bar."""
    bar = _bar("Screening")
    with bar:
        task = bar.add_task("screen", total=total)

        def report(record: dict[str, Any]) -> None:
            bar.console.print(paper_row(record, min_year))
            bar.advance(task)

        yield report


def summary_table(records: list[dict[str, Any]], reused: int) -> Table:
    """Counts for this run's records, plus papers reused from earlier runs."""
    labels = Counter(badge(r) for r in records if r["status"] == "screened")
    skips = Counter(r.get("skip_reason") for r in records if r["status"] == "skipped")
    failed = Counter(r["status"] for r in records if r["status"] in ("refused", "invalid", "error"))
    usage = [((r.get("provenance") or {}).get("usage") or {}) for r in records]
    tokens_in = sum(u.get("input_tokens", 0) for u in usage)
    tokens_out = sum(u.get("output_tokens", 0) for u in usage)

    rows: list[Fact] = [
        ("Included", sum(labels[k] for k in INCLUDED), breakdown(labels, INCLUDED), "bold green"),
        ("Excluded", labels["EXCLUDE"], "", "bold red"),
        ("Skipped", sum(skips.values()), breakdown(skips)),
    ]
    if failed:
        rows.append(
            (
                "Failed",
                sum(failed.values()),
                breakdown(failed) + " · retried next run",
                "bold magenta",
            )
        )
    if reused:
        rows.append(("Reused", reused, "from earlier runs"))
    if tokens_in or tokens_out:
        rows.append(("Tokens", "", f"{tokens_in:,} in · {tokens_out:,} out"))
    return facts(rows)


def summary_panel(
    records: list[dict[str, Any]], reused: int, title: str, footer: str = ""
) -> Panel:
    """The screening summary in a yellow box."""
    return boxed(title, summary_table(records, reused), footer)


def print_summary(records: list[dict[str, Any]], reused: int, title: str, footer: str = "") -> None:
    console.print()
    console.print(summary_panel(records, reused, title, footer))


# --- Status ----------------------------------------------------------------------------


def status_table(rows: list[tuple[str, str | None, str]], run_root: Path) -> Table:
    """`rows`: (stage, finished_at or None, what it produced)."""
    table = Table(
        title=Text(f"Run: {shorten_path(run_root)}", style=f"bold {ACCENT}"),
        title_justify="left",
        box=box.ROUNDED,
        border_style=ACCENT,
        header_style="bold",
    )
    table.add_column("Stage")
    table.add_column("", justify="center")
    table.add_column("Finished (UTC)", style="dim")
    table.add_column("Output", overflow="fold")
    for stage, finished, output in rows:
        done = bool(finished) or bool(output and stage == "ask")
        mark = Text("✓", style="bold green") if done else Text("–", style="dim")
        when = finished[:16].replace("T", " ") if finished else ""
        table.add_row(Text(stage, style="" if done else "dim"), mark, when, output)
    return table


# --- Ask ---------------------------------------------------------------------------------


def _source_text(s: dict[str, Any]) -> Text:
    line = Text("  ")
    line.append(f"[{s['tag']}]", style=f"bold {ACCENT}")
    line.append(f" {s.get('title') or ''}")
    if s.get("year"):
        line.append(f" ({s['year']})", style="dim")
    where = f"https://doi.org/{s['doi']}" if s.get("doi") else (s.get("url") or "")
    if where:
        line.append(f"\n        {where}", style="dim underline")
    if not s.get("known", True):
        line.append("  unknown tag", style="red")
    return line


def answer_view(result: dict[str, Any]) -> Group:
    """The answer in a box, then its sources, then the privacy line."""
    parts: list[Any] = [boxed("Answer", Text(result["answer"]))]
    if result["sources"]:
        parts.append(Text("Sources", style="bold"))
        parts += [_source_text(s) for s in result["sources"]]
    elif result["retrieved"] and not result["aborted"]:
        parts.append(Text("Sources (retrieved, not cited by the model)", style="bold"))
        parts += [_source_text(s) for s in result["retrieved"]]
    elif not result["aborted"]:
        parts.append(Text("No sources: nothing was retrieved.", style="dim"))

    summary = result.get("privacy_report_summary")
    sent = (summary or {}).get("sanitized_query")
    if sent and sent.strip() != result["question"].strip():
        parts += [
            Text(""),
            Text(f"⚠ Privacy mode sent your question as: {sent}", style=ACCENT),
            Text(
                "  If a name was masked by mistake, rephrase it or use --no-privacy.", style="dim"
            ),
        ]
    if summary:
        parts += [Text(""), Text(privacy_line(summary), style="dim")]
    return Group(*parts)


def privacy_line(summary: dict[str, Any]) -> str:
    def masked(count: int, entities: dict[str, int] | None) -> str:
        if not count:
            return "nothing masked"
        kinds = ", ".join(f"{k} {v}" for k, v in (entities or {}).items())
        return f"{count} masked ({kinds})" if kinds else f"{count} masked"

    question = masked(summary.get("question_masked", 0), summary.get("question_entities"))
    context = masked(summary.get("spans_masked", 0), summary.get("entities"))
    return f"Privacy: {summary['outcome']} · question: {question} · context: {context}"
