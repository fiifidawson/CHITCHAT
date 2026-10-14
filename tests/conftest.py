from __future__ import annotations

import shutil
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A temp folder with the example configs and a pipeline.yaml at its root."""
    shutil.copytree(REPO / "configs", tmp_path / "configs")
    shutil.copy(REPO / "configs" / "pipeline.example.yaml", tmp_path / "pipeline.yaml")
    return tmp_path
