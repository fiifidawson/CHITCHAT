"""The decision brief as a dict (brief.json), Markdown (brief.md) and a terminal view."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from chitchat.agents.loop import LoopResult
from chitchat.agents.schemas import CAVEAT

CONFLICT_NAMES = {
    "hierarchy": "stronger vs weaker study designs",
    "context": "different settings or populations",
    "noise": "small, old or unclear studies",
}


def build_brief(question: str, result: LoopResult, model: str) -> dict[str, Any]:
    """brief.json: the kept draft plus where it came from."""
    best = result.best
    assert best is not None
    critique = best.critique
    return {
        "question": question,
        **best.draft.model_dump(),
        "caveat": CAVEAT,
        "plan": result.plan.model_dump(),
        "rounds": len(result.rounds),
        "kept_round": best.number,
        "stopped_because": result.stopped_because,
        "verdict": critique.verdict if critique else None,
        "scores": critique.scores.model_dump() if critique else None,
        "warnings": best.checks.problems,
        "evidence_passages": len(result.evidence.passages),
        "model": model,
        "written_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def _cite(tags: list[str]) -> str:
    return " " + " ".join(f"[{t}]" for t in tags) if tags else ""


def _claim(claim: dict[str, Any]) -> str:
    hypothesis = " *(hypothesis)*" if claim.get("support") == "hypothesis" else ""
    return f"{claim['text']}{_cite(claim.get('sources') or [])}{hypothesis}"


def _source_line(tag: str, sources: dict[str, dict[str, Any]]) -> str:
    s = sources.get(tag) or {}
    where = f"https://doi.org/{s['doi']}" if s.get("doi") else (s.get("url") or "")
    year = f" ({s['year']})" if s.get("year") else ""
    title = s.get("title") or "unknown source"
    return f"- [{tag}] {title}{year} {where}".rstrip()


def brief_tags(brief: dict[str, Any]) -> list[str]:
    from chitchat.agents.checks import cited_tags
    from chitchat.agents.schemas import BriefDraft

    return cited_tags(BriefDraft.model_validate(brief))


def brief_markdown(brief: dict[str, Any], sources: dict[str, dict[str, Any]]) -> str:
    lines = ["# Decision brief", "", f"**Question:** {brief['question']}", ""]
    lines += ["## Bottom line", "", brief["bottom_line"], ""]
    lines += ["## Options", ""]
    for option in brief["options"]:
        lines += [f"### {option['name']}", "", option["description"], ""]
        lines.append(f"Evidence strength: **{option['evidence_strength']}**")
        lines.append("")
        if option["benefits"]:
            lines += ["Benefits:", *[f"- {_claim(c)}" for c in option["benefits"]], ""]
        if option["risks"]:
            lines += ["Risks:", *[f"- {_claim(c)}" for c in option["risks"]], ""]
    if brief["tradeoffs"]:
        names = [o["name"] for o in brief["options"]]
        lines += ["## Trade-offs", "", "| Criterion | " + " | ".join(names) + " |"]
        lines.append("|---|" + "---|" * len(names))
        for row in brief["tradeoffs"]:
            by_option = {a["option"]: a for a in row["assessments"]}
            cells = []
            for name in names:
                a = by_option.get(name)
                text = f"{a['assessment']}{_cite(a['sources'])}" if a else "—"
                cells.append(text.replace("|", "/"))
            lines.append(f"| {row['criterion']} | " + " | ".join(cells) + " |")
        lines.append("")
    if brief["conflicts"]:
        lines += ["## Where the evidence disagrees", ""]
        for c in brief["conflicts"]:
            kind = CONFLICT_NAMES.get(c["conflict_type"], c["conflict_type"])
            lines.append(f"- **{c['issue']}** ({kind})")
            lines += [f"  - {_claim(p)}" for p in c["positions"]]
        lines.append("")
    if brief["considerations"]:
        lines += ["## If this matters most", ""]
        for c in brief["considerations"]:
            because = f"{c['because']}{_cite(c['sources'])}"
            lines.append(f"- **{c['priority']}** → {c['option']}, because {because}")
        lines.append("")
    if brief["gaps"]:
        lines += ["## Gaps in the evidence", "", *[f"- {g}" for g in brief["gaps"]], ""]
    tags = brief_tags(brief)
    if tags:
        lines += ["## Sources", "", *[_source_line(t, sources) for t in tags], ""]
    lines += ["---", "", f"*{brief['caveat']}*", ""]
    scores = brief.get("scores") or {}
    score = f", Critic score {sum(scores.values())}/{2 * len(scores)}" if scores else ""
    lines.append(
        f"Model: {brief['model']}. {brief['rounds']} round(s), {brief['stopped_because']}{score}."
    )
    if brief.get("warnings"):
        lines += ["", "Checks that still fail:", *[f"- {w}" for w in brief["warnings"]]]
    return "\n".join(lines) + "\n"


def brief_view(brief: dict[str, Any], sources: dict[str, dict[str, Any]]) -> Any:
    """The brief in yellow boxes, for the terminal."""
    from rich.console import Group
    from rich.table import Table
    from rich.text import Text

    from chitchat import ui

    def cited(text: str, tags: list[str], hypothesis: bool = False) -> Text:
        line = Text(text)
        for t in tags:
            line.append(f" [{t}]", style=f"bold {ui.ACCENT}")
        if hypothesis:
            line.append("  hypothesis", style="italic dim")
        return line

    parts: list[Any] = [
        ui.boxed("Decision brief", Text(brief["bottom_line"]), footer=f"Q: {brief['question']}")
    ]
    for option in brief["options"]:
        body: list[Any] = [Text(option["description"], style="dim")]
        for label, key, colour in (("+", "benefits", "green"), ("−", "risks", "red")):
            for c in option[key]:
                line = Text(f"{label} ", style=f"bold {colour}")
                line.append_text(cited(c["text"], c["sources"], c["support"] == "hypothesis"))
                body.append(line)
        parts.append(
            ui.boxed(
                f"{option['name']} · evidence {option['evidence_strength']}",
                Group(*body),
                colour="white",
            )
        )
    if brief["tradeoffs"]:
        names = [o["name"] for o in brief["options"]]
        table = Table(title="Trade-offs", title_style=f"bold {ui.ACCENT}", show_lines=True)
        table.add_column("Criterion", style="bold")
        for name in names:
            table.add_column(name, overflow="fold")
        for row in brief["tradeoffs"]:
            by_option = {a["option"]: a for a in row["assessments"]}
            cells = [
                cited(by_option[n]["assessment"], by_option[n]["sources"])
                if n in by_option
                else "—"
                for n in names
            ]
            table.add_row(row["criterion"], *cells)
        parts.append(table)
    if brief["conflicts"]:
        body = []
        for c in brief["conflicts"]:
            kind = CONFLICT_NAMES.get(c["conflict_type"], c["conflict_type"])
            body.append(Text.assemble((c["issue"], "bold"), (f"  {kind}", "dim")))
            body += [cited(f"  • {p['text']}", p["sources"]) for p in c["positions"]]
        parts.append(ui.boxed("Where the evidence disagrees", Group(*body), colour="white"))
    if brief["considerations"]:
        body = [
            Text.assemble(
                (f"{c['priority']}", "bold"), " → ", (c["option"], f"bold {ui.ACCENT}")
            ).append_text(cited(f", because {c['because']}", c["sources"]))
            for c in brief["considerations"]
        ]
        parts.append(ui.boxed("If this matters most", Group(*body), colour="white"))
    if brief["gaps"]:
        body = [Text(f"• {g}") for g in brief["gaps"]]
        parts.append(ui.boxed("Gaps in the evidence", Group(*body), colour="white"))
    tags = brief_tags(brief)
    if tags:
        parts.append(Text("Sources", style="bold"))
        parts += [Text(_source_line(t, sources)[2:], style="dim") for t in tags]
    parts.append(Text(brief["caveat"], style="italic dim"))
    for warning in brief.get("warnings") or []:
        parts.append(Text(f"⚠ {warning}", style=ui.ACCENT))
    return Group(*parts)
