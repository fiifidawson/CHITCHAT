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
    from chitchat.status import last_runs, stage_durations, status_rows

    cfg = _load(config)
    run_dir = RunDir(cfg.run_root)
    rows = status_rows(run_dir, list(STAGES))
    ui.out.print(ui.status_table(rows, run_dir.root, stage_durations(run_dir)))
    runs = last_runs(run_dir)
    if runs:
        ui.out.print(ui.history_table(runs))


@app.command()
def search(
    question: Annotated[
        str | None, typer.Argument(help="Your research question, in plain words.")
    ] = None,
    config: Annotated[
        Path, typer.Option("--config", "-c", help="Template config with your settings.")
    ] = Path("pipeline.yaml"),
    mode: Annotated[
        str | None,
        typer.Option(
            help="deep (clarifying questions, several angles, full text) or shallow (quick)."
        ),
    ] = None,
    predefined: Annotated[
        bool, typer.Option(help="Use the config's predefined search instead of drafting one.")
    ] = False,
    run_name: Annotated[
        str | None, typer.Option(help="Folder name for this run. Default: from the question.")
    ] = None,
    yes: Annotated[
        bool, typer.Option("--yes", "-y", help="No questions: accept the first draft and run.")
    ] = False,
    plan_only: Annotated[
        bool, typer.Option(help="Plan the search and set up the run folder, but don't run it.")
    ] = False,
) -> None:
    """Plan a search from your question, confirm it, then run the pipeline in a new folder."""
    from rich.prompt import Confirm
    from rich.text import Text

    from chitchat import ui
    from chitchat.screening.llm import FatalLLMError, build_chat_model
    from chitchat.search.drafting import Drafter
    from chitchat.search.plan import PlanError
    from chitchat.search.session import (
        ConsoleIO,
        new_run_folder,
        plan_search,
        question_masker,
        save_plan,
        write_run_config,
    )
    from chitchat.stages import StageError

    cfg = _load(config)
    mode = mode or cfg.search.mode
    if mode not in ("deep", "shallow"):
        raise _fail("--mode must be deep or shallow.")
    if not predefined and not (question or "").strip():
        raise _fail('Give a research question, e.g. chitchat search "…", or use --predefined.')
    preset = cfg.search.preset(mode)
    try:
        run_root = new_run_folder(cfg.runs_dir, question, run_name)
    except ValueError as e:
        raise _fail(str(e)) from None

    if predefined:
        ui.note(f"Using the predefined search in {ui.shorten_path(cfg.discovery.config)}.")
        run_config = write_run_config(config, cfg, run_root, cfg.discovery.config, mode=None)
    else:
        assert question is not None
        ui.console.rule(
            Text(f" Planning a {mode} search ", style=f"bold {ui.ACCENT}"),
            style=ui.ACCENT,
            align="left",
        )
        ui.note(f"Question: {question}")
        try:
            chat_model, provider = build_chat_model(cfg.search_llm)
            if cfg.privacy.rag_privacy_config:
                ui.note("Checking your question for personal data (local, no LLM)…")
            result = plan_search(
                question,
                mode,
                preset,
                Drafter(chat_model),
                ConsoleIO(),
                mask=question_masker(cfg.privacy.rag_privacy_config),
                auto_accept=yes,
            )
        except FatalLLMError as e:
            from chitchat.stages.screen import _key_hint

            raise _fail(f"{e}{_key_hint(provider)}") from None
        except (ConfigError, PlanError, StageError) as e:
            raise _fail(str(e)) from None
        if result is None:
            ui.note("Search not saved. Nothing was run.")
            raise typer.Exit(0)
        run = RunDir(run_root)
        discovery = save_plan(run, result, preset)
        run_config = write_run_config(config, cfg, run_root, discovery, mode)

    ui.console.print()
    ui.print_box(
        "Search ready",
        [
            ("Mode", "", "predefined" if predefined else mode),
            ("Run folder", "", ui.shorten_path(run_root)),
            ("Config", "", ui.shorten_path(run_config)),
        ],
        footer=f"Run it later: chitchat run -c {ui.shorten_path(run_config)}",
    )
    if plan_only:
        return
    if not yes and not Confirm.ask("Run the pipeline now?", default=True, console=ui.console):
        return
    _run_stages(
        run_config, list(STAGES), command="search", mode="predefined" if predefined else mode
    )
    ui.note(f'Ask questions: chitchat ask -c {ui.shorten_path(run_config)} "your question"')


def _run_stages(
    config: Path,
    names: list[str],
    redecide: bool = False,
    command: str = "run",
    mode: str | None = None,
) -> None:
    from chitchat import ui
    from chitchat.screening.criteria import CriteriaError
    from chitchat.stages import StageError
    from chitchat.stages.screen import run_screen
    from chitchat.timing import RunRecorder

    cfg = _load(config)
    run_dir = RunDir(cfg.run_root)
    run_dir.root.mkdir(parents=True, exist_ok=True)
    names = ["redecide"] if redecide else names
    footer = f"See what each stage produced: chitchat status -c {ui.shorten_path(config)}"
    with RunRecorder(run_dir, command, ui.shorten_path(config), mode or cfg.search.mode) as rec:
        try:
            for position, name in enumerate(names, 1):
                ui.stage_header(name, position, len(names))
                with rec.stage(name) as entry:
                    if name == "redecide":
                        run_screen(cfg, run_dir, redecide_only=True)
                    else:
                        STAGES[name](cfg, run_dir)
                        run_dir.mark_done(name)
                ui.stage_finished(name, entry["seconds"])
        except (ConfigError, CriteriaError, StageError) as e:
            rec.fail(str(e))
            rec.seconds = sum(s["seconds"] for s in rec.stages)
            ui.console.print()
            ui.console.print(ui.run_box(rec))
            raise _fail(str(e)) from None
        except KeyboardInterrupt:
            rec.outcome = "interrupted"
            rec.seconds = sum(s["seconds"] for s in rec.stages)
            ui.console.print()
            ui.console.print(ui.run_box(rec, "Stopped with Ctrl+C. Finished stages are kept."))
            raise
        rec.outcome = "done"
        rec.seconds = sum(s["seconds"] for s in rec.stages)
        ui.console.print()
        ui.console.print(ui.run_box(rec, footer))


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
    # Windows without Developer Mode can't use symlinks; Hugging Face copies files instead.
    warnings.filterwarnings("ignore", message=".*cache-system uses symlinks.*")


def main() -> None:
    # mmore sets chunk ids from hash(text). A fixed seed keeps them stable.
    # UTF-8 mode: some libraries print emoji, which the Windows console code page can't encode.
    if os.environ.get("PYTHONHASHSEED") != "0" or os.environ.get("PYTHONUTF8") != "1":
        env = {
            **os.environ,
            "PYTHONHASHSEED": "0",
            "PYTHONUTF8": "1",
            "HF_HUB_DISABLE_SYMLINKS_WARNING": os.environ.get(
                "HF_HUB_DISABLE_SYMLINKS_WARNING", "1"
            ),
        }
        cmd = [sys.executable, "-m", "chitchat.cli", *sys.argv[1:]]
        raise SystemExit(subprocess.call(cmd, env=env))

    _quiet_library_warnings()
    from chitchat.ui import ConsoleLogHandler

    logging.basicConfig(level=logging.WARNING, format="%(message)s", handlers=[ConsoleLogHandler()])
    log.setLevel(logging.INFO)
    logging.getLogger("presidio-analyzer").setLevel(logging.ERROR)
    # Model download notices (e.g. "hf_xet is not installed"). Downloads still work.
    logging.getLogger("huggingface_hub").setLevel(logging.ERROR)

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
