"""A tiny real run. Needs network and models, so it is skipped by default.

Run it with:  uv run pytest -m slow
- Screening and ask need OPENAI_API_KEY (environment or .env).
- Index and ask need Milvus. Set CHITCHAT_MILVUS_URI to override the default
  (http://127.0.0.1:19530 on Windows, a Milvus Lite file elsewhere).
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import pytest
import yaml

from chitchat.config import load_pipeline_config
from chitchat.jsonl import read_json, read_jsonl
from chitchat.run_dir import RunDir

pytestmark = pytest.mark.slow
REPO = Path(__file__).resolve().parents[1]


def _milvus_uri(tmp_path: Path) -> str:
    default = "http://127.0.0.1:19530" if sys.platform == "win32" else str(tmp_path / "m.db")
    return os.environ.get("CHITCHAT_MILVUS_URI", default)


def _milvus_up(uri: str) -> bool:
    if "://" not in uri:
        return True  # Milvus Lite starts on demand
    from pymilvus import MilvusClient

    try:
        MilvusClient(uri=uri, timeout=5)
        return True
    except Exception:
        return False


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """Repo configs, with discovery cut down to arXiv, one category, 3 results."""
    shutil.copytree(REPO / "configs", tmp_path / "configs")
    disc_path = tmp_path / "configs" / "discovery" / "discovery.smoke.yaml"
    disc = yaml.safe_load(disc_path.read_text(encoding="utf-8"))
    disc.update(sources=["arxiv"], max_results=3)
    disc_path.write_text(yaml.safe_dump(disc), encoding="utf-8")
    cats_path = tmp_path / "configs" / "discovery" / "categories.smoke.yaml"
    cats = yaml.safe_load(cats_path.read_text(encoding="utf-8"))
    first = next(iter(cats["categories"]))
    cats_path.write_text(yaml.safe_dump({"categories": {first: cats["categories"][first]}}))

    pipeline = yaml.safe_load((tmp_path / "configs" / "pipeline.smoke.yaml").read_text())
    pipeline["runs_dir"] = "../runs"
    pipeline["index"]["db_uri"] = _milvus_uri(tmp_path)
    pipeline["index"]["collection"] = "chitchat_integration"
    # Index every label, so the test has something to ask about.
    pipeline["index"]["include_labels"] = ["HIGH", "MEDIUM", "LOW", "EXCLUDE"]
    (tmp_path / "configs" / "pipeline.yaml").write_text(yaml.safe_dump(pipeline))
    return tmp_path


def test_tiny_real_run(project: Path) -> None:
    from dotenv import load_dotenv

    from chitchat.stages.discover import run_discover, run_queries
    from chitchat.stages.export import run_export
    from chitchat.stages.sanitize import run_sanitize

    load_dotenv(REPO / ".env")
    cfg = load_pipeline_config(project / "configs" / "pipeline.yaml")
    run = RunDir(cfg.run_root)

    assert run_queries(cfg, run)
    stats = run_discover(cfg, run)
    assert stats["n_unique"] > 0
    run_sanitize(cfg, run)
    papers = list(read_jsonl(run.papers_sanitized))
    assert len(papers) == stats["n_unique"]
    assert all(p["privacy"]["count"] >= 0 for p in papers)

    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("No OPENAI_API_KEY: stopping after sanitize.")

    from chitchat.stages.screen import run_screen

    counts = run_screen(cfg, run)
    assert counts["error"] == 0
    prisma = run_export(cfg, run)
    assert prisma["records_after_dedupe"] == stats["n_unique"]

    if not _milvus_up(cfg.index.db_uri):
        pytest.skip(f"Milvus not reachable at {cfg.index.db_uri}: stopping after export.")
    if prisma["screened"]["total"] == 0:
        pytest.skip("Nothing screened (all skipped): nothing to index.")

    from chitchat.ask import ask
    from chitchat.stages.index import run_index

    assert run_index(cfg, run) > 0
    result = ask(cfg, run, "What data do these papers use?", privacy=True)
    assert result["answer"]
    assert result["retrieved"]
    sources = read_json(run.sources)
    assert all(s["tag"] in sources for s in result["sources"])
