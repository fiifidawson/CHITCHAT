"""PRISMA counts. Every number is computed from run files, never typed in."""

from __future__ import annotations

from collections import Counter
from typing import Any

from chitchat.screening.criteria import Criteria

PDF_OK = ("downloaded", "cached")
INCLUDED = ("HIGH", "MEDIUM", "LOW")
FAILED = ("refused", "invalid", "error")


def rule_text(criteria: Criteria, index: int) -> str:
    rule = criteria.rules[index]
    conditions = " and ".join(c.text for c in rule.conditions) or "default"
    return f"rule {index}: {conditions}"


def compute_prisma(
    stats: dict[str, Any] | None,
    papers: list[dict[str, Any]],
    screening: dict[str, dict[str, Any]],
    n_own_documents: int,
    criteria: Criteria,
) -> dict[str, Any]:
    """`screening` maps paper_id to its latest record."""
    if stats:
        found = stats["found"]
        n_unique = stats["n_unique"]
        pdf_counts = Counter(stats["pdf_counts"])
    else:  # discover stats missing: fall back to the papers file
        found = dict(Counter(p.get("source") or "unknown" for p in papers))
        n_unique = len(papers)
        pdf_counts = Counter(p.get("pdf_status") or "unknown" for p in papers)

    skipped: Counter[str] = Counter()
    failed: Counter[str] = Counter()
    content: Counter[str] = Counter()
    excluded_rules: Counter[str] = Counter()
    included: Counter[str] = Counter()
    not_screened = 0
    for paper in papers:
        record = screening.get(paper["paper_id"])
        if record is None:
            not_screened += 1
            continue
        status = record["status"]
        if status == "skipped":
            skipped[record.get("skip_reason") or "unknown"] += 1
        elif status in FAILED:
            failed[status] += 1
        elif status == "screened":
            content[record["provenance"].get("content", "unknown")] += 1
            decision = record["decision"]
            if decision["label"] == "EXCLUDE":
                excluded_rules[rule_text(criteria, decision["rule_index"])] += 1
            else:
                included[decision["label"]] += 1

    n_found = sum(found.values())
    return {
        "criteria": criteria.ref,
        "identified": {"per_source": dict(found), "total": n_found},
        "duplicates_removed": n_found - n_unique,
        "records_after_dedupe": n_unique,
        "full_text": {
            "obtained": sum(pdf_counts[s] for s in PDF_OK),
            "not_obtained": {k: v for k, v in pdf_counts.items() if k not in PDF_OK},
        },
        "not_screened_yet": not_screened,
        "excluded_before_screening": {"total": sum(skipped.values()), **dict(skipped)},
        "screened": {
            "total": sum(content.values()),
            "full_text": content["full_text"],
            "abstract_only": content["abstract"],
        },
        "screening_failed": {"total": sum(failed.values()), **{k: failed[k] for k in FAILED}},
        "excluded_by_rules": {"total": sum(excluded_rules.values()), **dict(excluded_rules)},
        "included": {"total": sum(included.values()), **{k: included[k] for k in INCLUDED}},
        "own_documents_added": n_own_documents,
    }


def check_totals(prisma: dict[str, Any]) -> list[str]:
    """Problems where the boxes don't add up. Empty when all is well."""
    problems = []
    accounted = (
        prisma["not_screened_yet"]
        + prisma["excluded_before_screening"]["total"]
        + prisma["screening_failed"]["total"]
        + prisma["screened"]["total"]
    )
    if accounted != prisma["records_after_dedupe"]:
        problems.append(
            f"{prisma['records_after_dedupe']} records after dedupe, "
            f"but {accounted} are accounted for. Rerun discover and sanitize together."
        )
    if (
        prisma["excluded_by_rules"]["total"] + prisma["included"]["total"]
        != (prisma["screened"]["total"])
    ):
        problems.append("excluded + included does not equal screened.")
    return problems


def _breakdown(items: dict[str, int]) -> str:
    parts = [f"{k}: {v}" for k, v in items.items() if k != "total" and v]
    return "; ".join(parts) if parts else "none"


def render_markdown(p: dict[str, Any]) -> str:
    sources = ", ".join(f"{k} {v}" for k, v in p["identified"]["per_source"].items())
    ft = p["full_text"]
    lines = [
        "# PRISMA flow",
        "",
        f"Criteria: `{p['criteria']}`. All numbers come from the run files.",
        "",
        "## Identification",
        "",
        f"- Records identified: **{p['identified']['total']}** ({sources})",
        f"- Duplicates removed: **{p['duplicates_removed']}**",
        f"- Records after removing duplicates: **{p['records_after_dedupe']}**",
        f"- Full text obtained: **{ft['obtained']}**. "
        f"Not obtained: {sum(ft['not_obtained'].values())} ({_breakdown(ft['not_obtained'])})",
        "",
        "## Screening",
        "",
        f"- Excluded before screening: **{p['excluded_before_screening']['total']}** "
        f"({_breakdown(p['excluded_before_screening'])})",
        f"- Screened: **{p['screened']['total']}** "
        f"(full text {p['screened']['full_text']}, abstract only {p['screened']['abstract_only']})",
        f"- Screening failed: **{p['screening_failed']['total']}** "
        f"({_breakdown(p['screening_failed'])})",
        f"- Not screened yet: **{p['not_screened_yet']}**",
        f"- Excluded by rules: **{p['excluded_by_rules']['total']}** "
        f"({_breakdown(p['excluded_by_rules'])})",
        "",
        "## Included",
        "",
        f"- Included: **{p['included']['total']}** "
        f"(HIGH {p['included']['HIGH']}, MEDIUM {p['included']['MEDIUM']}, "
        f"LOW {p['included']['LOW']})",
        f"- Own documents added: **{p['own_documents_added']}**",
        "",
        "## Diagram",
        "",
        "```mermaid",
        "flowchart TD",
        f'  A["Identified: {p["identified"]["total"]}"] --> B["After dedupe: '
        f'{p["records_after_dedupe"]}"]',
        f'  A -.-> D["Duplicates: {p["duplicates_removed"]}"]',
        f'  B --> C["Screened: {p["screened"]["total"]}"]',
        f'  B -.-> S["Excluded before screening: {p["excluded_before_screening"]["total"]}"]',
        f'  B -.-> F["Failed or not screened: '
        f'{p["screening_failed"]["total"] + p["not_screened_yet"]}"]',
        f'  C -.-> X["Excluded by rules: {p["excluded_by_rules"]["total"]}"]',
        f'  C --> I["Included: {p["included"]["total"]}"]',
        f'  O["Own documents: {p["own_documents_added"]}"] --> I2["Indexed with included papers"]',
        "  I --> I2",
        "```",
        "",
    ]
    return "\n".join(lines)
