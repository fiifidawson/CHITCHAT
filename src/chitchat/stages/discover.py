"""Stage 1: find papers with mmore Paper Discovery."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from chitchat.config import PipelineConfig
from chitchat.jsonl import write_json
from chitchat.run_dir import RunDir

log = logging.getLogger(__name__)


def _key(value: Any) -> str:
    """Plain string for an enum or str key."""
    return str(getattr(value, "value", value))


def discovery_stats(pipeline: Any) -> dict[str, Any]:
    """PRISMA counts from a finished PaperDiscoveryPipeline."""
    found = {_key(k): int(v) for k, v in pipeline.found.items()}
    n_unique = int(pipeline.n_unique)
    return {
        "found": found,
        "n_found": sum(found.values()),
        "n_unique": n_unique,
        "duplicates_removed": sum(found.values()) - n_unique,
        "pdf_counts": {_key(k): int(v) for k, v in pipeline.pdf_counts.items()},
        "failed_list": str(pipeline.failed_list) if pipeline.failed_list else None,
    }


def _resolve(base: Path, value: str) -> str:
    p = Path(value)
    return str(p if p.is_absolute() else (base / p).resolve())


def run_discover(cfg: PipelineConfig, run: RunDir) -> dict[str, Any]:
    from mmore.paper_discovery import PaperDiscoveryConfig, PaperDiscoveryPipeline
    from mmore.utils import load_config

    config_path = cfg.discovery.config
    disc = load_config(str(config_path), PaperDiscoveryConfig)
    base = config_path.parent
    disc.synonyms_path = _resolve(base, disc.synonyms_path)
    disc.categories_path = _resolve(base, disc.categories_path)
    disc.output_file = str(run.papers_raw)
    disc.pdf_dir = str(run.pdfs)
    disc.multimodal_output_file = None
    run.raw.mkdir(parents=True, exist_ok=True)

    pipeline = PaperDiscoveryPipeline(disc)
    papers = pipeline.run()
    stats = discovery_stats(pipeline)
    write_json(run.discovery_stats, stats)

    log.info("Found %d papers, %d after removing duplicates.", stats["n_found"], stats["n_unique"])
    for status, count in sorted(stats["pdf_counts"].items()):
        log.info("  PDF %s: %d", status, count)
    if stats["failed_list"]:
        log.info(
            "Some PDFs are missing. Save them at the `save_as` paths in %s and rerun.",
            stats["failed_list"],
        )
    log.info("Wrote %d papers to %s", len(papers), run.papers_raw)
    return stats
