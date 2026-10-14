"""Stage 7: chunk the included papers and own documents, and index them in Milvus.

Only sanitized text is indexed. Each chunk starts with its source tag, e.g. `[P0007] `,
because mmore RAG passes only the chunk text and file_path to the answer LLM.
"""

from __future__ import annotations

import logging
from typing import Any

from chitchat.config import PipelineConfig
from chitchat.jsonl import read_json, read_jsonl
from chitchat.run_dir import RunDir
from chitchat.screening.store import ScreeningStore
from chitchat.stages import StageError

log = logging.getLogger(__name__)

PROCESSOR_TYPE = "chitchat"


def select_items(
    papers: list[dict[str, Any]],
    screening: dict[str, dict[str, Any]],
    docs: list[dict[str, Any]],
    sources: dict[str, dict[str, Any]],
    include_labels: list[str],
    include_docs: bool,
) -> list[dict[str, Any]]:
    """`[{tag, text, extra}]` to index. Papers need an included label; full text, else abstract."""
    tags = {s["id"]: tag for tag, s in sources.items()}
    items = []
    for p in papers:
        label = ((screening.get(p["paper_id"]) or {}).get("decision") or {}).get("label")
        if label not in include_labels:
            continue
        text = (p.get("extracted_text") or "").strip() or (p.get("abstract") or "").strip()
        if text:
            extra = {k: p.get(k) for k in ("title", "year", "doi", "url")}
            items.append(
                {"tag": tags[p["paper_id"]], "text": text, "extra": extra | {"label": label}}
            )
    if include_docs:
        for d in docs:
            text = (d.get("text") or "").strip()
            if text:
                items.append({"tag": tags[d["doc_id"]], "text": text, "extra": {"kind": "own"}})
    return items


def prefix_tag(text: str, tag: str) -> str:
    return f"[{tag}] {text}"


def _chunk(items: list[dict[str, Any]], run: RunDir) -> list[Any]:
    from mmore.process.post_processor.pipeline import PPPipeline, PPPipelineConfig
    from mmore.type import DocumentMetadata, MultimodalSample
    from mmore.utils import load_config

    samples = [
        MultimodalSample(
            text=item["text"],
            modalities=[],
            metadata=DocumentMetadata(
                file_path=item["tag"], processor_type=PROCESSOR_TYPE, extra=item["extra"]
            ),
        )
        for item in items
    ]
    pp_config = {
        "pp_modules": [{"type": "chunker", "args": {"chunking_strategy": "sentence"}}],
        "output": {"output_path": str(run.chunks)},
    }
    chunks = PPPipeline.from_config(load_config(pp_config, PPPipelineConfig))(samples)
    for chunk in chunks:
        chunk.text = prefix_tag(chunk.text, chunk.metadata.file_path)
    return chunks


def milvus_error(uri: str, error: Exception) -> StageError:
    """A clear message for Milvus problems."""
    message = getattr(error, "message", None) or str(error)
    hint = ""
    if "connect" in message.lower() or "unavailable" in message.lower():
        hint = " Is Milvus running? On Windows, start it with `docker compose up -d` (see README)."
    return StageError(f"Milvus at {uri}: {message}.{hint}")


def _reset_collection(uri: str, db_name: str, collection: str) -> None:
    """Create the database if needed and drop the old collection: each run rebuilds it."""
    from pymilvus import MilvusClient

    if "://" in uri:  # Milvus standalone. Milvus Lite has only the default database.
        admin = MilvusClient(uri=uri)
        if db_name not in admin.list_databases():
            log.info("Creating Milvus database %r", db_name)
            admin.create_database(db_name)
    client = MilvusClient(uri=uri, db_name=db_name)
    if client.has_collection(collection):
        log.info("Dropping old collection %r", collection)
        client.drop_collection(collection)


def run_index(cfg: PipelineConfig, run: RunDir) -> int:
    if not run.sources.exists():
        raise StageError(f"Missing {run.sources}. Run the export stage first.")
    papers = list(read_jsonl(run.papers_sanitized)) if run.papers_sanitized.exists() else []
    docs = list(read_jsonl(run.docs_sanitized)) if run.docs_sanitized.exists() else []
    screening = ScreeningStore(run.screening).latest()
    ix = cfg.index
    items = select_items(
        papers, screening, docs, read_json(run.sources), ix.include_labels, ix.include_own_documents
    )
    if not items:
        raise StageError(
            f"Nothing to index: no papers labelled {', '.join(ix.include_labels)} "
            "and no own documents. Run screen first."
        )
    n_docs = sum(1 for i in items if i["tag"].startswith("D"))
    log.info("Indexing %d papers and %d own documents", len(items) - n_docs, n_docs)

    chunks = _chunk(items, run)
    log.info("Made %d chunks", len(chunks))

    from mmore.index.indexer import Indexer, IndexerConfig
    from mmore.utils import load_config
    from pymilvus.exceptions import MilvusException

    indexer_config = load_config(
        {
            "dense_model": {"model_name": ix.dense_model, "is_multimodal": False},
            "sparse_model": {"model_name": ix.sparse_model, "is_multimodal": False},
            "db": {"uri": ix.db_uri, "name": ix.db_name},
        },
        IndexerConfig,
    )
    try:
        _reset_collection(ix.db_uri, ix.db_name, ix.collection)
        Indexer.from_documents(
            config=indexer_config, documents=chunks, collection_name=ix.collection
        )
    except MilvusException as e:
        raise milvus_error(ix.db_uri, e) from None
    log.info("Indexed into collection %r at %s", ix.collection, ix.db_uri)
    return len(chunks)
