from __future__ import annotations

from pathlib import Path

import pytest
from rich.console import Console

from chitchat import ui
from chitchat.jsonl import read_jsonl
from chitchat.run_dir import RunDir
from chitchat.stages import StageError
from chitchat.status import last_runs, stage_durations
from chitchat.timing import RunRecorder, format_duration


@pytest.fixture
def recorded(monkeypatch: pytest.MonkeyPatch) -> Console:
    console = Console(width=100, record=True, force_terminal=False)
    monkeypatch.setattr(ui, "console", console)
    return console


@pytest.mark.parametrize(
    ("seconds", "text"),
    [(4.24, "4.2s"), (59.9, "59.9s"), (192, "3m 12s"), (3600, "1h 00m"), (3900, "1h 05m")],
)
def test_format_duration(seconds: float, text: str) -> None:
    assert format_duration(seconds) == text


def test_done_run_is_recorded(tmp_path: Path, recorded: Console) -> None:
    run = RunDir(tmp_path)
    with RunRecorder(run, "run", "pipeline.yaml", "deep") as rec:
        with rec.stage("queries"):
            recorded.print("built 8 queries")
        with rec.stage("discover"):
            pass
    [entry] = list(read_jsonl(run.history))
    assert entry["outcome"] == "done" and entry["error"] is None
    assert entry["command"] == "run" and entry["mode"] == "deep"
    assert [s["name"] for s in entry["stages"]] == ["queries", "discover"]
    assert all(s["status"] == "done" and s["seconds"] >= 0 for s in entry["stages"])

    log = rec.log_path.read_text(encoding="utf-8")
    assert rec.log_path.parent == run.logs and rec.log_path.name == f"{rec.run_id}.log"
    assert "chitchat run" in log and "outcome:  done" in log and "built 8 queries" in log


def test_failed_stage_is_recorded_and_logged(tmp_path: Path, recorded: Console) -> None:
    run = RunDir(tmp_path)
    with pytest.raises(StageError), RunRecorder(run, "run", "pipeline.yaml") as rec:
        with rec.stage("sanitize"):
            pass
        with rec.stage("screen"):
            raise StageError("no API key")
    [entry] = list(read_jsonl(run.history))
    assert entry["outcome"] == "failed" and "no API key" in entry["error"]
    assert [(s["name"], s["status"]) for s in entry["stages"]] == [
        ("sanitize", "done"),
        ("screen", "failed"),
    ]
    assert entry["stages"][1]["error"] == "no API key"
    assert rec.log_path.exists()  # written even though the run failed


def test_interrupted_run(tmp_path: Path, recorded: Console) -> None:
    run = RunDir(tmp_path)
    with (
        pytest.raises(KeyboardInterrupt),
        RunRecorder(run, "run", "p.yaml") as rec,
        rec.stage("discover"),
    ):
        raise KeyboardInterrupt
    [entry] = list(read_jsonl(run.history))
    assert entry["outcome"] == "interrupted"
    assert entry["stages"][0]["status"] == "interrupted"


def test_status_reads_history(tmp_path: Path, recorded: Console) -> None:
    run = RunDir(tmp_path)
    for _ in range(2):
        with RunRecorder(run, "run", "p.yaml") as rec, rec.stage("discover"):
            pass
    with (
        pytest.raises(StageError),
        RunRecorder(run, "run", "p.yaml") as rec,
        rec.stage("discover"),
    ):
        raise StageError("x")
    runs = last_runs(run)
    assert len(runs) == 3 and runs[0]["outcome"] == "failed"  # newest first
    assert "discover" in stage_durations(run)  # from the last run where it finished


def test_run_box(tmp_path: Path, recorded: Console) -> None:
    with pytest.raises(StageError), RunRecorder(RunDir(tmp_path), "run", "p.yaml") as rec:
        with rec.stage("discover"):
            pass
        rec_ref = rec
        with rec.stage("screen"):
            raise StageError("bad key")
    rec_ref.outcome = "failed"
    console = Console(width=100, record=True, force_terminal=False)
    console.print(ui.run_box(rec_ref, "see status"))
    text = console.export_text()
    assert "Failed" in text.splitlines()[0]
    assert "✓ discover" in text and "✗ screen" in text and "bad key" in text
    assert "Total" in text and rec_ref.run_id in text and "see status" in text
