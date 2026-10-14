"""Choose the text sent to the screening LLM."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

MIN_ABSTRACT_CHARS = 300
CUT_MARK = "\n[…]\n"


@dataclass(frozen=True)
class Content:
    text: str
    kind: str  # full_text | abstract
    truncated: bool


def head_tail(text: str, max_chars: int) -> tuple[str, bool]:
    """Keep the first 70% and last 30% of the budget."""
    if len(text) <= max_chars:
        return text, False
    head = int(max_chars * 0.7)
    tail = max_chars - head
    return text[:head] + CUT_MARK + text[-tail:], True


def select_content(
    paper: dict[str, Any], min_chars: int, max_chars: int, use_abstract: bool
) -> tuple[Content | None, str | None]:
    """Return (content, None) or (None, skip_reason)."""
    full = (paper.get("extracted_text") or "").strip()
    abstract = (paper.get("abstract") or "").strip()

    if full and len(full) >= min_chars:
        text, truncated = head_tail(full, max_chars)
        return Content(text, "full_text", truncated), None
    if use_abstract and len(abstract) >= MIN_ABSTRACT_CHARS:
        if len(abstract) < min_chars:
            return None, "text_too_short"
        text, truncated = head_tail(abstract, max_chars)
        return Content(text, "abstract", truncated), None
    if not full and not abstract:
        return None, "no_text"
    return None, "text_too_short"
