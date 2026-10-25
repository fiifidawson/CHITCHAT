"""The Retriever: searches the run's index. No LLM.

Chunks come back with their source tag ([P0007], [D0002]) in `metadata.file_path` and at the
start of the text. They were sanitized before indexing.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from chitchat.config import PipelineConfig

# (query, k) -> documents (LangChain Documents or dicts with page_content and metadata).
Search = Callable[[str, int], list[Any]]


def retriever_settings(cfg: PipelineConfig, k: int) -> dict[str, Any]:
    """mmore RetrieverConfig for the run's index. Shared by `ask` and the agents."""
    from chitchat.stages.index import milvus_db_name

    return {
        "db": {
            "uri": cfg.index.db_uri,
            "name": milvus_db_name(cfg.index.db_uri, cfg.index.db_name),
        },
        "collection_name": cfg.index.collection,
        "k": k,
        "hybrid_search_weight": 0.5,
        "reranker_model_name": cfg.ask.reranker,
    }


def milvus_search(cfg: PipelineConfig, k: int) -> Search:
    """A search function over the run's Milvus collection."""
    from mmore.rag.retriever import Retriever, RetrieverConfig
    from mmore.utils import load_config
    from pymilvus.exceptions import MilvusException

    from chitchat.stages import StageError
    from chitchat.stages.index import milvus_error

    try:
        retriever = Retriever.from_config(load_config(retriever_settings(cfg, k), RetrieverConfig))
    except MilvusException as e:
        raise milvus_error(cfg.index.db_uri, e) from None
    except ValueError as e:
        if "collection" not in str(e):
            raise
        raise StageError(
            f"No index called {cfg.index.collection!r} yet. Run the index stage first."
        ) from None

    def search(query: str, k: int) -> list[Any]:
        try:
            return retriever.invoke({"input": query, "collection_name": cfg.index.collection}, k=k)
        except MilvusException as e:
            raise milvus_error(cfg.index.db_uri, e) from None

    return search


def _field(doc: Any, name: str) -> Any:
    return doc.get(name) if isinstance(doc, dict) else getattr(doc, name, None)


@dataclass
class Passage:
    tag: str
    chunk_id: str
    text: str
    query: str  # the search that found it


@dataclass
class Evidence:
    """Every passage retrieved so far, without repeats, up to `max_chars` of text."""

    max_chars: int
    passages: list[Passage] = field(default_factory=list)
    dropped: int = 0  # passages left out because of the character cap

    @property
    def chars(self) -> int:
        return sum(len(p.text) for p in self.passages)

    def tags(self) -> set[str]:
        return {p.tag for p in self.passages}

    def add(self, docs: list[Any], query: str) -> int:
        """Add new passages. Returns how many were new."""
        seen = {p.chunk_id for p in self.passages}
        added = 0
        for doc in docs:
            metadata = _field(doc, "metadata") or {}
            text = (_field(doc, "page_content") or "").strip()
            tag = metadata.get("file_path") or ""
            chunk_id = str(metadata.get("id") or f"{tag}:{hash(text)}")
            if not tag or not text or chunk_id in seen:
                continue
            if self.chars + len(text) > self.max_chars:
                self.dropped += 1
                continue
            self.passages.append(Passage(tag, chunk_id, text, query))
            seen.add(chunk_id)
            added += 1
        return added

    def render(self) -> str:
        """The passages for a prompt. Each starts with its tag."""
        blocks = []
        for p in self.passages:
            text = p.text if p.text.startswith(f"[{p.tag}]") else f"[{p.tag}] {p.text}"
            blocks.append(text)
        return "\n\n".join(blocks)

    def to_json(self) -> list[dict[str, Any]]:
        return [
            {"tag": p.tag, "chunk_id": p.chunk_id, "query": p.query, "text": p.text}
            for p in self.passages
        ]
