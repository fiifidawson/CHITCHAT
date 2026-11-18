"""Paths inside runs/<run>/ and stage markers.

Raw text lives only in raw/. Everything else holds sanitized text.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class RunDir:
    root: Path

    @property
    def config(self) -> Path:
        """The pipeline config written by `chitchat search` for this run."""
        return self.root / "pipeline.yaml"

    @property
    def search(self) -> Path:
        """The drafted search: synonyms, categories, discovery config and plan."""
        return self.root / "search"

    @property
    def plan(self) -> Path:
        return self.search / "plan.json"

    @property
    def history(self) -> Path:
        """One line per command run on this folder: stages, durations, outcome."""
        return self.root / "history.jsonl"

    @property
    def logs(self) -> Path:
        return self.root / "logs"

    @property
    def queries(self) -> Path:
        return self.root / "queries.json"

    # Raw data. Never share this folder.
    @property
    def raw(self) -> Path:
        return self.root / "raw"

    @property
    def papers_raw(self) -> Path:
        return self.raw / "papers.jsonl"

    @property
    def pdfs(self) -> Path:
        return self.raw / "pdfs"

    @property
    def discovery_stats(self) -> Path:
        return self.raw / "discovery_stats.json"

    @property
    def docs_process(self) -> Path:
        return self.raw / "docs_process"

    @property
    def docs_raw(self) -> Path:
        return self.raw / "docs.jsonl"

    # Sanitized data and results.
    @property
    def papers_sanitized(self) -> Path:
        return self.root / "papers.sanitized.jsonl"

    @property
    def docs_sanitized(self) -> Path:
        return self.root / "docs.sanitized.jsonl"

    @property
    def privacy_report(self) -> Path:
        return self.root / "privacy_report.json"

    @property
    def screening(self) -> Path:
        return self.root / "screening.jsonl"

    @property
    def dataset_jsonl(self) -> Path:
        return self.root / "dataset.jsonl"

    @property
    def dataset_csv(self) -> Path:
        return self.root / "dataset.csv"

    @property
    def prisma_json(self) -> Path:
        return self.root / "prisma.json"

    @property
    def prisma_md(self) -> Path:
        return self.root / "prisma.md"

    @property
    def chunks(self) -> Path:
        return self.root / "index" / "chunks.jsonl"

    @property
    def sources(self) -> Path:
        return self.root / "sources.json"

    @property
    def answers(self) -> Path:
        return self.root / "answers.jsonl"

    # The answer stage: a decision brief for the run's question.
    @property
    def answer(self) -> Path:
        return self.root / "answer"

    @property
    def brief_json(self) -> Path:
        return self.answer / "brief.json"

    @property
    def brief_md(self) -> Path:
        return self.answer / "brief.md"

    @property
    def evidence(self) -> Path:
        return self.answer / "evidence.json"

    @property
    def trace(self) -> Path:
        return self.answer / "trace.jsonl"

    @property
    def eval(self) -> Path:
        return self.root / "eval"

    # Stage markers.
    def _marker(self, stage: str) -> Path:
        return self.root / ".done" / stage

    def mark_done(self, stage: str) -> None:
        marker = self._marker(stage)
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(datetime.now(UTC).isoformat(), encoding="utf-8")

    def is_done(self, stage: str) -> bool:
        return self._marker(stage).exists()

    def done_at(self, stage: str) -> str | None:
        marker = self._marker(stage)
        return marker.read_text(encoding="utf-8").strip() if marker.exists() else None
