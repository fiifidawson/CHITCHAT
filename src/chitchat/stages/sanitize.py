"""Stage 3: mask personal data with mmore's privacy agents. No LLM is called.

The config is fully pinned (domain, engine, threshold, entity types),
so mmore never asks an LLM and never prompts.
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from chitchat.config import ConfigError, PipelineConfig
from chitchat.ids import paper_id
from chitchat.jsonl import read_jsonl, write_json, write_jsonl
from chitchat.run_dir import RunDir

log = logging.getLogger(__name__)

PART_CHARS = 5_000
PAPERS = "papers"
OWN_DOCUMENTS = "own_documents"


# --- Config -------------------------------------------------------------------


def load_sanitize_configs(path: Path) -> dict[str, dict[str, Any]]:
    """Two mmore PrivacyConfig dicts from one file: one for papers, one for own documents."""
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    detection = dict(data.get("detection") or {})
    problems = []
    if not data.get("domain"):
        problems.append("domain")
    if not detection.get("engine"):
        problems.append("detection.engine")
    if detection.get("confidence_threshold") is None:
        problems.append("detection.confidence_threshold")
    lists = {
        PAPERS: detection.pop("entity_types_papers", None),
        OWN_DOCUMENTS: detection.pop("entity_types_own_documents", None),
    }
    for kind, entities in lists.items():
        if not entities:
            problems.append(f"detection.entity_types_{kind}")
    if problems:
        raise ConfigError(
            f"{path}: set {', '.join(problems)}. "
            "Without them mmore would call an LLM to pick values."
        )
    if data.get("interactive"):
        raise ConfigError(f"{path}: `interactive` must be false for batch sanitizing.")

    configs = {}
    for kind, entities in lists.items():
        configs[kind] = {**data, "detection": {**detection, "entity_types": list(entities)}}
    return configs


# --- Splitting ------------------------------------------------------------------


def split_text(text: str, size: int = PART_CHARS) -> list[str]:
    """Split on paragraph breaks into parts of about `size` chars. `"".join` gives the text back."""
    if len(text) <= size:
        return [text]
    pieces = re.split(r"(?<=\n\n)", text)
    parts: list[str] = []
    current = ""
    for piece in pieces:
        while len(piece) > size:  # one huge paragraph
            if current:
                parts.append(current)
                current = ""
            parts.append(piece[:size])
            piece = piece[size:]
        if current and len(current) + len(piece) > size:
            parts.append(current)
            current = ""
        current += piece
    if current:
        parts.append(current)
    return parts


# --- Sanitizer ------------------------------------------------------------------


class Sanitizer:
    """Wraps mmore's analyzer, detector and sanitizer. Build once and reuse: models load once."""

    def __init__(self, analyzer: Any, detector: Any, sanitizer: Any) -> None:
        self.analyzer = analyzer
        self.detector = detector
        self.sanitizer = sanitizer

    @classmethod
    def from_dict(cls, privacy_config: dict[str, Any]) -> Sanitizer:
        from mmore.privacy.agents.analyzer import ContextPolicyAnalyzerAgent
        from mmore.privacy.agents.detector import DetectorAgent
        from mmore.privacy.agents.sanitizer import SanitizerAgent
        from mmore.privacy.config import PrivacyConfig
        from mmore.utils import load_config

        cfg = load_config(privacy_config, PrivacyConfig)
        return cls(
            ContextPolicyAnalyzerAgent.from_config(cfg),
            DetectorAgent.from_config(cfg),
            SanitizerAgent.from_config(cfg),
        )

    def sanitize(self, texts: list[str | None]) -> tuple[list[str | None], dict[str, Any]]:
        """Sanitize the texts of ONE document in one call, so `[PERSON_1]` stays consistent.

        Returns the clean texts (None and "" pass through) and a report with no original values.
        """
        chunks: list[str] = []
        owners: list[int] = []
        for i, text in enumerate(texts):
            if text:
                for part in split_text(text):
                    chunks.append(part)
                    owners.append(i)
        if not chunks:
            return list(texts), {"count": 0, "entities": {}, "level": "low"}

        policy = self.analyzer.build_policy("", chunks)
        spans, risk = self.detector.detect(policy, chunks)
        clean = self.sanitizer.sanitize(policy, chunks, spans)

        out: list[str | None] = [t if not t else "" for t in texts]
        for owner, part in zip(owners, clean, strict=True):
            out[owner] = (out[owner] or "") + part
        report = {"count": risk.count, "entities": dict(risk.entity_counts), "level": risk.level}
        return out, report


# --- Stage ----------------------------------------------------------------------


def _totals(reports: list[dict[str, Any]]) -> dict[str, Any]:
    entities: Counter[str] = Counter()
    levels: Counter[str] = Counter()
    for r in reports:
        entities.update(r["entities"])
        levels[r["level"]] += 1
    return {
        "documents": len(reports),
        "spans": sum(r["count"] for r in reports),
        "entities": dict(entities),
        "risk_levels": dict(levels),
    }


def sanitize_papers(papers: list[dict[str, Any]], sanitizer: Sanitizer) -> list[dict[str, Any]]:
    out = []
    for i, paper in enumerate(papers, 1):
        (abstract, text), report = sanitizer.sanitize(
            [paper.get("abstract"), paper.get("extracted_text")]
        )
        out.append(
            {
                **paper,
                "paper_id": paper_id(paper),
                "abstract": abstract,
                "extracted_text": text,
                "privacy": report,
            }
        )
        if i % 10 == 0 or i == len(papers):
            log.info("  papers: %d/%d", i, len(papers))
    return out


def sanitize_docs(docs: list[dict[str, Any]], sanitizer: Sanitizer) -> list[dict[str, Any]]:
    out = []
    for doc in docs:
        (text,), report = sanitizer.sanitize([doc.get("text")])
        out.append({**doc, "text": text, "privacy": report})
    return out


def run_sanitize(cfg: PipelineConfig, run: RunDir) -> dict[str, Any]:
    configs = load_sanitize_configs(cfg.privacy.sanitize_config)
    report: dict[str, Any] = {}

    if run.papers_raw.exists():
        papers = list(read_jsonl(run.papers_raw))
        log.info("Sanitizing %d papers", len(papers))
        clean = sanitize_papers(papers, Sanitizer.from_dict(configs[PAPERS]))
        write_jsonl(run.papers_sanitized, clean)
        report[PAPERS] = _totals([p["privacy"] for p in clean])
    else:
        log.info("No papers yet (%s). Run discover first.", run.papers_raw)

    if run.docs_raw.exists():
        docs = list(read_jsonl(run.docs_raw))
        log.info("Sanitizing %d own documents", len(docs))
        clean = sanitize_docs(docs, Sanitizer.from_dict(configs[OWN_DOCUMENTS]))
        write_jsonl(run.docs_sanitized, clean)
        report[OWN_DOCUMENTS] = _totals([d["privacy"] for d in clean])

    write_json(run.privacy_report, report)
    for kind, totals in report.items():
        log.info("  %s: %d spans masked %s", kind, totals["spans"], totals["entities"])
    return report
