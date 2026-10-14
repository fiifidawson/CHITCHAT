"""screening.jsonl: one record per paper, appended as soon as it is done."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from chitchat.jsonl import append_jsonl, read_jsonl, write_jsonl
from chitchat.screening.criteria import Criteria
from chitchat.screening.rules import decide
from chitchat.screening.schema import answer_values

# Records with these statuses are reused. refused, invalid and error are retried.
FINAL_STATUSES = ("screened", "skipped")


def resume_key(record: dict[str, Any]) -> tuple[str, str, str]:
    prov = record.get("provenance") or {}
    return record["paper_id"], prov.get("criteria_hash", ""), prov.get("model", "")


class ScreeningStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def records(self) -> list[dict[str, Any]]:
        return list(read_jsonl(self.path)) if self.path.exists() else []

    def done_ids(self, criteria_hash: str, model: str) -> set[str]:
        """Paper ids already screened or skipped with these criteria and this model."""
        return {
            r["paper_id"]
            for r in self.records()
            if r.get("status") in FINAL_STATUSES and resume_key(r)[1:] == (criteria_hash, model)
        }

    def append(self, record: dict[str, Any]) -> None:
        append_jsonl(self.path, record)

    def latest(self) -> dict[str, dict[str, Any]]:
        """The last record per paper_id."""
        return {r["paper_id"]: r for r in self.records()}


def redecide(path: Path, criteria: Criteria) -> int:
    """Recompute `decision` from stored answers with the current rules. No LLM calls.

    Only records screened with the current criteria hash are touched.
    Returns how many labels changed.
    """
    store = ScreeningStore(path)
    records = store.records()
    changed = 0
    for record in records:
        if record.get("status") != "screened":
            continue
        if (record.get("provenance") or {}).get("criteria_hash") != criteria.hash:
            continue
        decision = decide(list(criteria.rules), answer_values(record.get("answers") or {}))
        if (record.get("decision") or {}).get("label") != decision["label"]:
            changed += 1
        record["decision"] = decision
    tmp = path.with_suffix(".jsonl.tmp")
    write_jsonl(tmp, records)
    os.replace(tmp, path)
    return changed
