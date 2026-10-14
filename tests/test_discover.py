from __future__ import annotations

import json
from collections import Counter
from enum import StrEnum
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from chitchat.stages.discover import OPENALEX_MAX_CHARS, discovery_stats, too_long_for_openalex

REPO = Path(__file__).resolve().parents[1]


class FakeStatus(StrEnum):
    DOWNLOADED = "downloaded"
    REFUSED = "refused"


def test_discovery_stats() -> None:
    pipeline = SimpleNamespace(
        found=Counter({"openalex": 10, "arxiv": 5}),
        n_unique=12,
        pdf_counts=Counter({FakeStatus.DOWNLOADED: 8, FakeStatus.REFUSED: 4}),
        failed_list=Path("runs/x/raw/papers_failed_pdfs.csv"),
    )
    stats = discovery_stats(pipeline)
    assert stats["found"] == {"openalex": 10, "arxiv": 5}
    assert stats["n_found"] == 15
    assert stats["duplicates_removed"] == 3
    assert stats["pdf_counts"] == {"downloaded": 8, "refused": 4}
    assert stats["failed_list"].endswith("papers_failed_pdfs.csv")
    json.dumps(stats)


def test_discovery_stats_no_failures() -> None:
    pipeline = SimpleNamespace(found=Counter(), n_unique=0, pdf_counts=Counter(), failed_list=None)
    assert discovery_stats(pipeline)["failed_list"] is None


@pytest.mark.parametrize(("filename", "n"), [("categories.yaml", 8), ("categories.smoke.yaml", 2)])
def test_categories_reference_known_words(filename: str, n: int) -> None:
    folder = REPO / "configs" / "discovery"
    with open(folder / "synonyms.jsonl", encoding="utf-8") as f:
        words = {json.loads(line)["word"].lower() for line in f if line.strip()}
    categories = yaml.safe_load((folder / filename).read_text(encoding="utf-8"))
    assert len(categories["categories"]) == n
    for name, keys in categories["categories"].items():
        missing = [k for k in keys if k.lower() not in words]
        assert not missing, f"{name}: {missing}"


def test_too_long_for_openalex() -> None:
    queries = [
        {"category": "short", "query": "x" * OPENALEX_MAX_CHARS},
        {"category": "long", "query": "x" * (OPENALEX_MAX_CHARS + 1)},
    ]
    assert too_long_for_openalex(queries, ["openalex", "arxiv"]) == ["long"]
    assert too_long_for_openalex(queries, ["arxiv", "europepmc"]) == []
