"""Masking off by default, and `chitchat run` carrying on where it stopped. No LLM, no network."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from chitchat import cli
from chitchat.config import load_pipeline_config
from chitchat.jsonl import read_json, read_jsonl, write_jsonl
from chitchat.run_dir import RunDir
from chitchat.stages.sanitize import run_sanitize

runner = CliRunner()


# --- Masking off ---------------------------------------------------------------------------


def test_with_masking_off_the_text_passes_through(project: Path) -> None:
    cfg = load_pipeline_config(project / "pipeline.yaml")
    run = RunDir(cfg.run_root)
    paper = {"title": "T", "doi": "10.1/x", "abstract": "Alice Smith wrote this."}
    write_jsonl(run.papers_raw, [paper])
    write_jsonl(run.docs_raw, [{"doc_id": "D0001", "text": "Call Bob on 555-0101."}])

    report = run_sanitize(cfg, run)  # loads no detector: Presidio isn't touched

    [masked] = list(read_jsonl(run.papers_sanitized))
    assert masked["abstract"] == paper["abstract"] and masked["paper_id"]
    [doc] = list(read_jsonl(run.docs_sanitized))
    assert doc["text"] == "Call Bob on 555-0101."
    assert (
        report
        == read_json(run.privacy_report)
        == {
            "masking": "off",
            "papers": 1,
            "own_documents": 1,
        }
    )


def test_status_says_masking_is_off(project: Path) -> None:
    cfg = load_pipeline_config(project / "pipeline.yaml")
    run_sanitize(cfg, RunDir(cfg.run_root))
    out = runner.invoke(cli.app, ["status", "-c", str(project / "pipeline.yaml")]).output
    assert "masking off" in out


def test_every_run_says_masking_is_off(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "STAGES", {"queries": lambda cfg, run: None})
    result = runner.invoke(cli.app, ["run", "-c", str(project / "pipeline.yaml")])
    assert result.exit_code == 0, result.output
    assert "Masking is off" in result.output


# --- Resuming --------------------------------------------------------------------------------


def _fake_stages(
    monkeypatch: pytest.MonkeyPatch, screened: int = 0, fail_at: str | None = None
) -> list[str]:
    ran: list[str] = []

    def stage(name: str) -> Any:
        def run(cfg: Any, run_dir: Any) -> Any:
            if name == fail_at:
                from chitchat.stages import StageError

                raise StageError(f"{name} broke")
            ran.append(name)
            return Counter({"screened": screened}) if name == "screen" else None

        return run

    names = ["queries", "discover", "sanitize", "screen", "export", "answer"]
    monkeypatch.setattr(cli, "STAGES", {n: stage(n) for n in names})
    return ran


def _run(project: Path, *extra: str) -> Any:
    return runner.invoke(cli.app, ["run", "-c", str(project / "pipeline.yaml"), *extra])


def test_a_stopped_run_carries_on_from_where_it_stopped(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ran = _fake_stages(monkeypatch, fail_at="screen")
    assert _run(project).exit_code == 2
    assert ran == ["queries", "discover", "sanitize"]

    ran = _fake_stages(monkeypatch, screened=5)
    result = _run(project)
    assert result.exit_code == 0, result.output
    assert ran == ["screen", "export", "answer"]  # the search isn't redone
    assert "done earlier, skipped" in result.output


def test_nothing_new_to_screen_skips_the_rest(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_stages(monkeypatch, screened=5)
    assert _run(project).exit_code == 0
    ran = _fake_stages(monkeypatch, screened=0)
    result = _run(project)
    assert ran == ["screen"]  # screening checks for unscreened or failed papers, then stops
    assert "Everything was already done" in result.output


def test_named_stages_run_even_if_done(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_stages(monkeypatch, screened=5)
    assert _run(project).exit_code == 0
    ran = _fake_stages(monkeypatch)
    assert _run(project, "--stages", "discover,answer").exit_code == 0
    assert ran == ["discover", "answer"]
