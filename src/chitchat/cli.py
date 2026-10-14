"""The `chitchat` command."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any

import typer

from chitchat.config import ConfigError, PipelineConfig, load_pipeline_config
from chitchat.run_dir import RunDir

log = logging.getLogger("chitchat")

app = typer.Typer(no_args_is_help=True, add_completion=False, help="Literature-review pipeline.")

ConfigOption = Annotated[Path, typer.Option("--config", "-c", help="Path to pipeline.yaml.")]


def _queries(cfg: PipelineConfig, run: RunDir) -> None:
    from chitchat.stages.discover import run_queries

    run_queries(cfg, run)


def _discover(cfg: PipelineConfig, run: RunDir) -> None:
    from chitchat.stages.discover import run_discover

    run_discover(cfg, run)


def _ingest(cfg: PipelineConfig, run: RunDir) -> None:
    from chitchat.stages.ingest import run_ingest

    run_ingest(cfg, run)


def _sanitize(cfg: PipelineConfig, run: RunDir) -> None:
    from chitchat.stages.sanitize import run_sanitize

    run_sanitize(cfg, run)


def _screen(cfg: PipelineConfig, run: RunDir) -> None:
    from chitchat.stages.screen import run_screen

    run_screen(cfg, run)


# Stages in run order.
STAGES: dict[str, Callable[[PipelineConfig, RunDir], Any]] = {
    "queries": _queries,
    "discover": _discover,
    "ingest": _ingest,
    "sanitize": _sanitize,
    "screen": _screen,
}


@app.callback()
def _root() -> None:
    """Literature-review pipeline."""


def _fail(message: str) -> typer.Exit:
    typer.secho(message, fg=typer.colors.RED, err=True)
    return typer.Exit(2)


def _load(config: Path) -> PipelineConfig:
    """Load and check every config file before any network or LLM call."""
    from chitchat.screening.criteria import CriteriaError, load_criteria
    from chitchat.stages.sanitize import load_sanitize_configs

    try:
        cfg = load_pipeline_config(config)
        load_criteria(cfg.screening.criteria)
        load_sanitize_configs(cfg.privacy.sanitize_config)
    except (ConfigError, CriteriaError) as e:
        raise _fail(str(e)) from None
    return cfg


def _parse_stages(value: str | None) -> list[str]:
    if not value:
        return list(STAGES)
    wanted = [s.strip() for s in value.split(",") if s.strip()]
    unknown = [s for s in wanted if s not in STAGES]
    if unknown:
        raise typer.BadParameter(
            f"unknown stage(s): {', '.join(unknown)}. Known: {', '.join(STAGES)}"
        )
    return [s for s in STAGES if s in wanted]


@app.command()
def run(
    config: ConfigOption = Path("pipeline.yaml"),
    stages: Annotated[
        str | None, typer.Option(help="Comma-separated stages to run. Default: all.")
    ] = None,
    redecide: Annotated[
        bool, typer.Option(help="Recompute labels from stored answers. No LLM calls.")
    ] = False,
) -> None:
    """Run pipeline stages."""
    from chitchat.screening.criteria import CriteriaError
    from chitchat.stages.screen import StageError, run_screen

    selected = _parse_stages(stages)
    cfg = _load(config)
    run_dir = RunDir(cfg.run_root)
    run_dir.root.mkdir(parents=True, exist_ok=True)
    try:
        if redecide:
            run_screen(cfg, run_dir, redecide_only=True)
            return
        for name in selected:
            log.info("== %s ==", name)
            STAGES[name](cfg, run_dir)
            run_dir.mark_done(name)
    except (ConfigError, CriteriaError, StageError) as e:
        raise _fail(str(e)) from None
    log.info("Done. Outputs are in %s", run_dir.root)


def main() -> None:
    # mmore sets chunk ids from hash(text). A fixed seed keeps them stable.
    if os.environ.get("PYTHONHASHSEED") != "0":
        env = {**os.environ, "PYTHONHASHSEED": "0"}
        cmd = [sys.executable, "-m", "chitchat.cli", *sys.argv[1:]]
        raise SystemExit(subprocess.call(cmd, env=env))

    from dotenv import load_dotenv

    load_dotenv()
    logging.basicConfig(level=logging.WARNING, format="%(message)s")
    log.setLevel(logging.INFO)
    logging.getLogger("presidio-analyzer").setLevel(logging.ERROR)
    app()


if __name__ == "__main__":
    main()
