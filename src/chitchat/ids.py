"""Stable ids for papers and own documents."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any


def _sha16(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def normalize_title(title: str) -> str:
    """Lowercase, keep only a-z and 0-9."""
    return re.sub(r"[^a-z0-9]", "", title.lower())


def paper_id(paper: dict[str, Any]) -> str:
    """`doi:<doi>`, or `title:<hash>` of the discovered title. Never the LLM's echo."""
    doi = (paper.get("doi") or "").strip().lower()
    if doi:
        return f"doi:{doi}"
    return f"title:{_sha16(normalize_title(paper.get('title') or '').encode('utf-8'))}"


def doc_id(path: Path) -> str:
    """`doc:<hash>` of the file's bytes."""
    return f"doc:{_sha16(path.read_bytes())}"
