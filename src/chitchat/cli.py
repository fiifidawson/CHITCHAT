"""The `chitchat` command."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import warnings
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any

import typer

from chitchat.config import ConfigError, PipelineConfig, load_pipeline_config, shadowed_keys
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


def _export(cfg: PipelineConfig, run: RunDir) -> None:
    from chitchat.stages.export import run_export

    run_export(cfg, run)


def _index(cfg: PipelineConfig, run: RunDir) -> None:
    from chitchat.stages.index import run_index

    run_index(cfg, run)


# Stages in run order.
STAGES: dict[str, Callable[[PipelineConfig, RunDir], Any]] = {
    "queries": _queries,
    "discover": _discover,
    "ingest": _ingest,
    "sanitize": _sanitize,
    "screen": _screen,
    "export": _export,
    "index": _index,
}


@app.callback()
def _root() -> None:
    """Literature-review pipeline."""


def _fail(message: str) -> typer.Exit:
    from rich.text import Text

    from chitchat import ui

    ui.console.print(Text(f"✗ {message}", style="bold red"))
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
    _run_stages(config, _parse_stages(stages), redecide=redecide)


@app.command()
def report(config: ConfigOption = Path("pipeline.yaml")) -> None:
    """Rebuild dataset.jsonl, dataset.csv and the PRISMA report from the run files."""
    _run_stages(config, ["export"])


@app.command()
def ask(
    question: Annotated[str, typer.Argument(help="Your question.")],
    config: ConfigOption = Path("pipeline.yaml"),
    no_privacy: Annotated[
        bool, typer.Option("--no-privacy", help="Skip mmore privacy mode.")
    ] = False,
    review: Annotated[
        bool, typer.Option("--review", help="Check the sanitized context yourself before sending.")
    ] = False,
    k: Annotated[int | None, typer.Option(help="How many chunks to retrieve.")] = None,
) -> None:
    """Answer a question from the index, with [P0001] citations."""
    from chitchat import ui
    from chitchat.ask import ask as run_ask
    from chitchat.stages import StageError

    cfg = _load(config)
    try:
        result = run_ask(cfg, RunDir(cfg.run_root), question, not no_privacy, review, k)
    except StageError as e:
        raise _fail(str(e)) from None
    ui.out.print(ui.answer_view(result))


@app.command()
def status(config: ConfigOption = Path("pipeline.yaml")) -> None:
    """Show which stages are done and what they produced."""
    from chitchat import ui
    from chitchat.status import status_rows

    cfg = _load(config)
    run_dir = RunDir(cfg.run_root)
    ui.out.print(ui.status_table(status_rows(run_dir, list(STAGES)), run_dir.root))


def _run_stages(config: Path, names: list[str], redecide: bool = False) -> None:
    from chitchat import ui
    from chitchat.screening.criteria import CriteriaError
    from chitchat.stages import StageError
    from chitchat.stages.screen import run_screen

    cfg = _load(config)
    run_dir = RunDir(cfg.run_root)
    run_dir.root.mkdir(parents=True, exist_ok=True)
    try:
        if redecide:
            ui.stage_header("redecide", 1, 1)
            run_screen(cfg, run_dir, redecide_only=True)
            return
        for position, name in enumerate(names, 1):
            ui.stage_header(name, position, len(names))
            STAGES[name](cfg, run_dir)
            run_dir.mark_done(name)
    except (ConfigError, CriteriaError, StageError) as e:
        raise _fail(str(e)) from None
    ui.console.print()
    ui.print_box(
        "Done",
        [("Stages", len(names), ", ".join(names)), ("Outputs", "", ui.shorten_path(run_dir.root))],
        footer=f"See what each stage produced: chitchat status -c {config}",
    )


def _quiet_library_warnings() -> None:
    """Hide library deprecation notices; they are not useful to someone running the pipeline."""
    # langchain and langchain_core turn their notices back on when imported, so import them first.
    import langchain  # noqa: F401
    from langchain_core._api.deprecation import (
        LangChainDeprecationWarning,
        LangChainPendingDeprecationWarning,
    )

    for category in (
        DeprecationWarning,
        PendingDeprecationWarning,
        FutureWarning,
        LangChainDeprecationWarning,
        LangChainPendingDeprecationWarning,
    ):
        warnings.filterwarnings("ignore", category=category)


def main() -> None:
    # mmore sets chunk ids from hash(text). A fixed seed keeps them stable.
    # UTF-8 mode: some libraries print emoji, which the Windows console code page can't encode.
    if os.environ.get("PYTHONHASHSEED") != "0" or os.environ.get("PYTHONUTF8") != "1":
        env = {**os.environ, "PYTHONHASHSEED": "0", "PYTHONUTF8": "1"}
        cmd = [sys.executable, "-m", "chitchat.cli", *sys.argv[1:]]
        raise SystemExit(subprocess.call(cmd, env=env))

    _quiet_library_warnings()
    from chitchat.ui import ConsoleLogHandler

    logging.basicConfig(level=logging.WARNING, format="%(message)s", handlers=[ConsoleLogHandler()])
    log.setLevel(logging.INFO)
    logging.getLogger("presidio-analyzer").setLevel(logging.ERROR)

    from dotenv import load_dotenv

    for name in shadowed_keys(dict(os.environ), Path(".env")):
        log.warning(
            "%s is set in your environment and in .env, with different values. "
            "The environment value is used. To use .env, remove it: "
            "`Remove-Item Env:%s` (PowerShell) or `unset %s` (bash).",
            name,
            name,
            name,
        )
    load_dotenv()
    app()


if __name__ == "__main__":
    main()
