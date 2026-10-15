"""Stage 1: find papers with mmore Paper Discovery."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from chitchat.config import PipelineConfig
from chitchat.jsonl import write_json
from chitchat.run_dir import RunDir

log = logging.getLogger(__name__)

# OpenAlex rejects longer searches (HTTP 400) unless you have a paid API key.
OPENALEX_MAX_CHARS = 1500


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


def _load_discovery_config(cfg: PipelineConfig, run: RunDir) -> Any:
    """The mmore config, with its paths resolved and outputs moved into the run folder."""
    from mmore.paper_discovery import PaperDiscoveryConfig
    from mmore.utils import load_config

    config_path = cfg.discovery.config
    disc = load_config(str(config_path), PaperDiscoveryConfig)
    base = config_path.parent
    disc.synonyms_path = _resolve(base, disc.synonyms_path)
    disc.categories_path = _resolve(base, disc.categories_path)
    disc.output_file = str(run.papers_raw)
    disc.pdf_dir = str(run.pdfs)
    disc.multimodal_output_file = None
    return disc


def _build_queries(disc: Any) -> list[dict[str, str]]:
    """The boolean query per category, as mmore builds it. Offline."""
    import yaml
    from mmore.paper_discovery.boolean import build_boolean_queries, load_synonyms

    synonyms = load_synonyms(disc.synonyms_path)
    with open(disc.categories_path, encoding="utf-8") as f:
        categories = yaml.safe_load(f)["categories"]
    return [
        {"category": q.combination_title, "query": q.boolean_combination}
        for q in build_boolean_queries(synonyms, categories)
    ]


def too_long_for_openalex(queries: list[dict[str, str]], sources: list[str]) -> list[str]:
    """Categories whose query OpenAlex will reject. Empty if OpenAlex is not a source."""
    if "openalex" not in sources:
        return []
    return [q["category"] for q in queries if len(q["query"]) > OPENALEX_MAX_CHARS]


def _warn_long_queries(queries: list[dict[str, str]], sources: list[str]) -> None:
    long = too_long_for_openalex(queries, sources)
    if long:
        log.warning(
            "OpenAlex will return nothing for %d of %d categories: their queries are over "
            "%d characters (%s). Europe PMC and arXiv still run. "
            "Shorten the synonyms or categories to include OpenAlex.",
            len(long),
            len(queries),
            OPENALEX_MAX_CHARS,
            ", ".join(long),
        )


def quiet_mupdf() -> None:
    """MuPDF prints a line for each odd PDF instruction it skips. The text is still read."""
    import pymupdf

    pymupdf.TOOLS.mupdf_display_errors(False)
    pymupdf.TOOLS.mupdf_display_warnings(False)


def run_queries(cfg: PipelineConfig, run: RunDir) -> list[dict[str, str]]:
    """Build the boolean queries offline and save them. No network calls."""
    disc = _load_discovery_config(cfg, run)
    queries = _build_queries(disc)
    write_json(run.queries, queries)

    from chitchat import ui

    limit = OPENALEX_MAX_CHARS if "openalex" in disc.sources else None
    ui.console.print(ui.queries_table(queries, limit))
    _warn_long_queries(queries, disc.sources)
    ui.note(f"Saved to {ui.shorten_path(run.queries)}")
    return queries


def run_discover(cfg: PipelineConfig, run: RunDir) -> dict[str, Any]:
    from mmore.paper_discovery import PaperDiscoveryPipeline

    disc = _load_discovery_config(cfg, run)
    run.raw.mkdir(parents=True, exist_ok=True)
    _warn_long_queries(_build_queries(disc), disc.sources)
    quiet_mupdf()

    pipeline = PaperDiscoveryPipeline(disc)
    papers = pipeline.run()
    stats = discovery_stats(pipeline)
    write_json(run.discovery_stats, stats)

    _print_summary(stats, run, len(papers))
    return stats


def _print_summary(stats: dict[str, Any], run: RunDir, n_papers: int) -> None:
    from chitchat import ui

    pdfs = stats["pdf_counts"]
    obtained = {k: v for k, v in pdfs.items() if k in ("downloaded", "cached")}
    missing = {k: v for k, v in pdfs.items() if k not in ("downloaded", "cached")}
    rows: list[ui.Fact] = [
        ("Found", stats["n_found"], ui.breakdown(stats["found"]) or "no source returned papers"),
        ("Duplicates", stats["duplicates_removed"], "removed"),
        ("Papers", stats["n_unique"], "after removing duplicates", "bold green"),
        ("Full text", sum(obtained.values()), ui.breakdown(obtained)),
    ]
    if missing:
        rows.append(("No PDF", sum(missing.values()), ui.breakdown(missing), "bold red"))
    footer = [f"Saved {n_papers} papers to {ui.shorten_path(run.papers_raw)}"]
    if stats["failed_list"]:
        footer.append(
            f"Missing PDFs: save them at the save_as paths in "
            f"{ui.shorten_path(stats['failed_list'])}, then rerun discover."
        )
    ui.console.print()
    ui.print_box("Discovery", rows, footer)
