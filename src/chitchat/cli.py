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


def _discover(cfg: PipelineConfig, run: RunDir) -> None:
    from chitchat.stages.discover import run_discover

    run_discover(cfg, run)


# Stages in run order.
STAGES: dict[str, Callable[[PipelineConfig, RunDir], Any]] = {
    "discover": _discover,
}


@app.callback()
def _root() -> None:
    """Literature-review pipeline."""


def _load(config: Path) -> PipelineConfig:
    try:
        return load_pipeline_config(config)
    except ConfigError as e:
        typer.secho(str(e), fg=typer.colors.RED, err=True)
        raise typer.Exit(2) from None


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
) -> None:
    """Run pipeline stages."""
    selected = _parse_stages(stages)
    cfg = _load(config)
    run_dir = RunDir(cfg.run_root)
    run_dir.root.mkdir(parents=True, exist_ok=True)
    for name in selected:
        log.info("== %s ==", name)
        STAGES[name](cfg, run_dir)
        run_dir.mark_done(name)
    log.info("Done. Outputs are in %s", run_dir.root)


def main() -> None:
    # mmore sets chunk ids from hash(text). A fixed seed keeps them stable.
    if os.environ.get("PYTHONHASHSEED") != "0":
        env = {**os.environ, "PYTHONHASHSEED": "0"}
        cmd = [sys.executable, "-m", "chitchat.cli", *sys.argv[1:]]
        raise SystemExit(subprocess.call(cmd, env=env))

    from dotenv import load_dotenv

    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    app()


if __name__ == "__main__":
    main()
