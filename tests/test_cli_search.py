"""CLI paths that need no LLM: predefined search, errors, and a timed offline run."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from chitchat.cli import app
from chitchat.config import load_pipeline_config
from chitchat.jsonl import read_jsonl
from chitchat.run_dir import RunDir

runner = CliRunner()


def test_search_needs_a_question(project: Path) -> None:
    result = runner.invoke(app, ["search", "-c", str(project / "pipeline.yaml")])
    assert result.exit_code == 2


def test_search_rejects_unknown_mode(project: Path) -> None:
    args = ["search", "q", "-c", str(project / "pipeline.yaml"), "--mode", "medium"]
    assert runner.invoke(app, args).exit_code == 2


def test_predefined_search_sets_up_a_run(project: Path) -> None:
    args = ["search", "--predefined", "--plan-only", "--run-name", "legacy-run"]
    result = runner.invoke(app, [*args, "-c", str(project / "pipeline.yaml")])
    assert result.exit_code == 0, result.output
    run = RunDir(project / "runs" / "legacy-run")
    cfg = load_pipeline_config(run.config)
    template = load_pipeline_config(project / "pipeline.yaml")
    assert cfg.run_root == run.root.resolve()
    assert cfg.discovery.config == template.discovery.config  # the predefined search
    assert cfg.index.collection == "run_legacy_run"


def test_run_records_history_and_log(project: Path) -> None:
    pytest.importorskip("mmore.paper_discovery")
    config = project / "pipeline.yaml"
    result = runner.invoke(app, ["run", "-c", str(config), "--stages", "queries"])
    assert result.exit_code == 0, result.output
    run = RunDir(load_pipeline_config(config).run_root)
    [entry] = list(read_jsonl(run.history))
    assert entry["outcome"] == "done" and entry["stages"][0]["name"] == "queries"
    logs = list(run.logs.glob("*.log"))
    assert len(logs) == 1 and "Boolean queries" in logs[0].read_text(encoding="utf-8")

    status = runner.invoke(app, ["status", "-c", str(config)])
    assert status.exit_code == 0 and "Recent runs" in status.output
