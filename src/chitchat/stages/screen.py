"""Stage 4: screen papers. The LLM answers the criteria; rules decide the label."""

from __future__ import annotations

import logging
import os
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from chitchat.config import PipelineConfig, ScreeningSettings, shadowed_keys
from chitchat.ids import paper_id
from chitchat.jsonl import read_jsonl
from chitchat.run_dir import RunDir
from chitchat.screening import prompt
from chitchat.screening.content import select_content
from chitchat.screening.criteria import Criteria, load_criteria
from chitchat.screening.llm import FatalLLMError, StructuredCaller, build_chat_model
from chitchat.screening.rules import decide
from chitchat.screening.schema import (
    answer_values,
    extraction_model,
    normalize_answers,
    normalize_extracted,
    screening_model,
)
from chitchat.screening.store import ScreeningStore, redecide
from chitchat.stages import StageError

log = logging.getLogger(__name__)

METADATA_FIELDS = ("year", "doi", "url", "source", "authors", "pdf_status", "search_category")


class Screener:
    """Screens one paper at a time. Thread-safe."""

    def __init__(
        self,
        criteria: Criteria,
        settings: ScreeningSettings,
        chat_model: Any,
        provider: str,
        sanitized: bool,
    ) -> None:
        self.criteria = criteria
        self.settings = settings
        self.model = settings.llm.llm_name
        self.provider = provider
        self.sanitized = sanitized
        self.screen_call = StructuredCaller(chat_model, screening_model(criteria))
        schema = extraction_model(criteria)
        self.extract_call = StructuredCaller(chat_model, schema) if schema else None
        self.fixed = prompt.fixed_part(criteria)
        self.extract_fixed = prompt.extract_fixed_part(criteria)

    def _record(self, paper: dict[str, Any], status: str, **extra: Any) -> dict[str, Any]:
        record: dict[str, Any] = {
            "paper_id": paper.get("paper_id") or paper_id(paper),
            "title": paper.get("title") or "",
            "status": status,
            "skip_reason": None,
            "decision": None,
            "answers": None,
            "extracted": None,
            # Metadata comes only from discovery, never from the LLM.
            "metadata": {k: paper.get(k) for k in METADATA_FIELDS},
            "provenance": {
                "criteria": self.criteria.ref,
                "criteria_hash": self.criteria.hash,
                "model": self.model,
                "provider": self.provider,
                "screened_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "sanitized": self.sanitized,
            },
        }
        provenance = extra.pop("provenance", {})
        record["provenance"].update(provenance)
        record.update(extra)
        return record

    def screen(self, paper: dict[str, Any]) -> dict[str, Any]:
        s = self.settings
        year = paper.get("year")
        if s.min_year and isinstance(year, int) and year < s.min_year:
            return self._record(paper, "skipped", skip_reason="before_min_year")

        content, skip = select_content(paper, s.min_chars, s.max_chars, s.use_abstract_if_no_text)
        if content is None:
            return self._record(paper, "skipped", skip_reason=skip)

        paper_text = prompt.paper_part(
            paper.get("title") or "", year, content.text, content.kind, content.truncated
        )
        provenance = {
            "content": content.kind,
            "input_chars": len(content.text),
            "truncated": content.truncated,
        }
        result = self.screen_call(prompt.build_messages(prompt.SYSTEM, self.fixed, paper_text))
        usage = dict(result.usage)
        if result.status != "ok":
            provenance["usage"] = usage
            return self._record(paper, result.status, error=result.error, provenance=provenance)

        answers = normalize_answers(result.parsed, self.criteria)
        decision = decide(list(self.criteria.rules), answer_values(answers))
        extracted = None
        extract_error = None
        if self.extract_call and decision["label"] != "EXCLUDE":
            ext = self.extract_call(
                prompt.build_messages(prompt.EXTRACT_SYSTEM, self.extract_fixed, paper_text)
            )
            for key, value in ext.usage.items():
                usage[key] = usage.get(key, 0) + value
            if ext.status == "ok":
                extracted = normalize_extracted(ext.parsed, self.criteria)
            else:
                extract_error = f"{ext.status}: {ext.error}"

        provenance["usage"] = usage
        record = self._record(
            paper,
            "screened",
            decision=decision,
            answers=answers,
            extracted=extracted,
            notes=getattr(result.parsed, "notes", ""),
            provenance=provenance,
        )
        if extract_error:
            record["extract_error"] = extract_error
        return record


def _key_hint(provider: str) -> str:
    """Explain the most common cause: an old key in the environment overriding .env."""
    name = f"{provider}_API_KEY"
    if name not in shadowed_keys(dict(os.environ), Path(".env")):
        return ""
    return (
        f" {name} is set in your environment and overrides the one in .env. "
        f"Remove it: `Remove-Item Env:{name}` (PowerShell) or `unset {name}` (bash)."
    )


def run_screen(cfg: PipelineConfig, run: RunDir, redecide_only: bool = False) -> Counter[str]:
    criteria = load_criteria(cfg.screening.criteria)

    if redecide_only:
        if not run.screening.exists():
            raise StageError(f"No screening results yet ({run.screening}).")
        changed = redecide(run.screening, criteria)
        log.info("Recomputed decisions with the current rules. %d labels changed.", changed)
        return Counter()

    sanitized = cfg.privacy.before_screening
    source = run.papers_sanitized if sanitized else run.papers_raw
    if not source.exists():
        step = "sanitize" if sanitized else "discover"
        raise StageError(f"Missing {source}. Run the {step} stage first.")
    if not sanitized:
        log.warning("privacy.before_screening is off: raw paper text goes to the LLM.")

    papers = list(read_jsonl(source))
    store = ScreeningStore(run.screening)
    model = cfg.screening.llm.llm_name
    done = store.done_ids(criteria.hash, model)
    todo = [p for p in papers if (p.get("paper_id") or paper_id(p)) not in done]
    reused = len(papers) - len(todo)
    log.info(
        "Screening %d of %d papers with %s (criteria %s). %d reused from earlier runs.",
        len(todo),
        len(papers),
        model,
        criteria.ref,
        reused,
    )
    counts: Counter[str] = Counter()
    if not todo:
        return counts

    from chitchat import ui

    chat_model, provider = build_chat_model(cfg.screening.llm)
    screener = Screener(criteria, cfg.screening, chat_model, provider, sanitized)
    records: list[dict] = []
    with (
        ThreadPoolExecutor(max_workers=cfg.screening.max_concurrency) as pool,
        ui.screening_progress(len(todo), cfg.screening.min_year) as report,
    ):
        futures = [pool.submit(screener.screen, p) for p in todo]
        for future in as_completed(futures):
            try:
                record = future.result()
            except FatalLLMError as e:
                pool.shutdown(cancel_futures=True)
                raise StageError(f"{e}{_key_hint(provider)} Finished papers are kept.") from None
            store.append(record)
            records.append(record)
            counts[record["status"]] += 1
            report(record)

    ui.print_summary(
        records,
        reused,
        title=f"Screening done · {model} · {criteria.ref}",
        footer=f"Saved to {run.screening}. Next: the export stage builds dataset.csv and PRISMA.",
    )
    return counts
