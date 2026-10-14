from __future__ import annotations

from pathlib import Path

from chitchat.run_dir import RunDir


def test_raw_files_stay_in_raw(tmp_path: Path) -> None:
    run = RunDir(tmp_path)
    for path in (run.papers_raw, run.pdfs, run.discovery_stats, run.docs_raw, run.docs_process):
        assert run.raw in path.parents
    for path in (run.papers_sanitized, run.docs_sanitized, run.screening, run.dataset_jsonl):
        assert run.raw not in path.parents


def test_stage_markers(tmp_path: Path) -> None:
    run = RunDir(tmp_path)
    assert not run.is_done("discover")
    run.mark_done("discover")
    assert run.is_done("discover")
    assert run.done_at("discover")
