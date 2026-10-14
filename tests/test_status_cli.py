from __future__ import annotations

from pathlib import Path

from chitchat.cli import STAGES, shadowed_keys
from chitchat.jsonl import write_json, write_jsonl
from chitchat.run_dir import RunDir
from chitchat.stages.index import milvus_error
from chitchat.status import render_status, stage_details


def _screening_record(n: int, status: str, label: str | None = None) -> dict:
    decision = {"label": label} if label else None
    return {"paper_id": f"doi:{n}", "status": status, "decision": decision}


def test_status_on_empty_run(tmp_path: Path) -> None:
    run = RunDir(tmp_path)
    assert stage_details(run) == {}
    text = render_status(run, list(STAGES))
    assert "queries" in text and "index" in text and "ask" in text
    assert "done" not in text


def test_status_details(tmp_path: Path) -> None:
    run = RunDir(tmp_path)
    write_json(run.queries, [{"category": "a", "query": "q"}, {"category": "b", "query": "q"}])
    write_json(
        run.discovery_stats,
        {"found": {"x": 3}, "n_unique": 3, "pdf_counts": {"downloaded": 2, "refused": 1}},
    )
    write_json(run.privacy_report, {"papers": {"spans": 12}})
    write_jsonl(
        run.screening,
        [
            _screening_record(1, "error"),
            _screening_record(1, "screened", "HIGH"),  # latest record wins
            _screening_record(2, "screened", "EXCLUDE"),
            _screening_record(3, "skipped"),
        ],
    )
    run.mark_done("discover")

    details = stage_details(run)
    assert details["queries"] == "2 queries"
    assert details["discover"] == "3 papers, 2 with PDF"
    assert details["sanitize"] == "papers: 12 spans masked"
    assert details["screen"] == "screened 2, skipped 1 (HIGH 1, MEDIUM 0, LOW 0, EXCLUDE 1)"

    text = render_status(run, list(STAGES))
    discover_line = next(line for line in text.splitlines() if line.strip().startswith("discover"))
    assert "done" in discover_line and "3 papers" in discover_line


def test_shadowed_keys(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "OPENAI_API_KEY=sk-new\nANTHROPIC_API_KEY=same\nOTHER=x\nMISTRAL_API_KEY=m\n",
        encoding="utf-8",
    )
    environ = {"OPENAI_API_KEY": "sk-old", "ANTHROPIC_API_KEY": "same", "OTHER": "y"}
    assert shadowed_keys(environ, env_file) == ["OPENAI_API_KEY"]
    assert shadowed_keys(environ, tmp_path / "missing.env") == []


def test_milvus_error_hint() -> None:
    class MilvusException(Exception):
        message = "Fail connecting to server on 127.0.0.1:19530"

    error = milvus_error("http://127.0.0.1:19530", MilvusException())
    assert "Is Milvus running?" in str(error)
    other = milvus_error("http://x", ValueError("bad schema"))
    assert "bad schema" in str(other) and "Is Milvus running?" not in str(other)
