"""`chitchat ask`: answer a question from the index, with [P0001] citations.

With privacy mode on, retrieved chunks go through mmore's privacy graph
before the answer LLM sees them.
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from datetime import UTC, datetime
from typing import Any

from chitchat.config import PipelineConfig
from chitchat.jsonl import append_jsonl, read_json
from chitchat.run_dir import RunDir
from chitchat.stages import StageError

log = logging.getLogger(__name__)

CITE_RULES = (
    "You answer questions about the papers and documents of a literature review. "
    "Use only the context. "
    "Each context passage starts with a source tag such as [P0007] or [D0002]. "
    "Cite the tags of the passages you use, in square brackets, like [P0007]. "
    "If the context does not answer the question, say so."
)
# mmore RAG fills {context}. In privacy mode the context goes in the user message instead.
RAG_PROMPT = CITE_RULES + "\n\nContext:\n{context}"

TAG = re.compile(r"\[([PD]\d{4})\]")
MASK = re.compile(r"\[([A-Z][A-Z_]*?)_\d+\]")  # [PERSON_1], [EMAIL_ADDRESS_2], ...
ABORTED_UNSAFE = "aborted-unsafe"
NO_ANSWER = "No answer: the privacy check stopped it. See the report."


def cited_tags(answer: str) -> list[str]:
    """Tags cited in the answer, in order, without repeats."""
    return list(dict.fromkeys(TAG.findall(answer or "")))


def _source(tag: str, sources: dict[str, dict[str, Any]]) -> dict[str, Any]:
    s = sources.get(tag) or {}
    return {
        "tag": tag,
        "title": s.get("title"),
        "year": s.get("year"),
        "doi": s.get("doi"),
        "url": s.get("url"),
        "known": tag in sources,
    }


def _plain(value: Any) -> str:
    """Enum value or plain string."""
    return str(getattr(value, "value", value) or "")


def privacy_summary(report: dict[str, Any] | None) -> dict[str, Any] | None:
    """A short PII-free summary of mmore's report."""
    if not report:
        return None
    detection = report.get("detection") or {}
    sent = report.get("sanitized_query") or None
    question_masks = Counter(MASK.findall(sent or ""))
    return {
        "outcome": _plain(report.get("outcome")),
        "spans_masked": detection.get("count", 0),  # in the retrieved context
        "entities": detection.get("entity_counts", {}),
        "question_masked": sum(question_masks.values()),
        "question_entities": dict(question_masks),
        "gate": _plain(report.get("gate_outcome")),
        "answer_model": report.get("answer_model"),
        # Already masked by mmore, so safe to keep and show.
        "sanitized_query": sent,
    }


def _file_path(doc: Any) -> str:
    """The tag of a retrieved chunk. mmore returns Documents dumped to dicts."""
    metadata = doc.get("metadata") if isinstance(doc, dict) else getattr(doc, "metadata", None)
    return (metadata or {}).get("file_path", "")


def format_result(
    question: str, out: dict[str, Any], sources: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """Turn mmore's RAG output into an answer with a sources list."""
    report = out.get("privacy_report")
    summary = privacy_summary(report)
    aborted = bool(summary and summary["outcome"] == ABORTED_UNSAFE)
    answer = (out.get("answer") or "").strip()
    if aborted or (summary and not answer):
        answer = NO_ANSWER

    retrieved = [_file_path(d) for d in out.get("docs") or []]
    cited = cited_tags(answer)
    return {
        "question": question,
        "answer": answer,
        "aborted": aborted,
        "sources": [_source(t, sources) for t in cited],
        "retrieved": [_source(t, sources) for t in dict.fromkeys(retrieved) if t],
        "privacy_report_summary": summary,
        "asked_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def _privacy_config(path: str, review: bool) -> Any:
    """Load the privacy config and add the citation rules to the answer prompt."""
    import yaml
    from mmore.privacy.config import PrivacyConfig
    from mmore.utils import load_config

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not (data.get("answer") or {}).get("llm"):
        raise StageError(f"{path}: privacy mode needs `answer.llm`; it answers with that LLM.")
    answer = data["answer"]
    answer["system_prompt"] = "\n\n".join(p for p in (answer.get("system_prompt"), CITE_RULES) if p)
    data["interactive"] = review
    return load_config(data, PrivacyConfig)


def ask(
    cfg: PipelineConfig,
    run: RunDir,
    question: str,
    privacy: bool = True,
    review: bool = False,
    k: int | None = None,
) -> dict[str, Any]:
    if not run.sources.exists():
        raise StageError(f"Missing {run.sources}. Run export and index first.")
    sources = read_json(run.sources)

    from mmore.privacy.runner import setup_privacy
    from mmore.rag.pipeline import RAGConfig, RAGPipeline
    from mmore.utils import load_config

    rag_config = load_config(
        {
            "retriever": {
                "db": {"uri": cfg.index.db_uri, "name": cfg.index.db_name},
                "collection_name": cfg.index.collection,
                "k": k or cfg.ask.k,
                "hybrid_search_weight": 0.5,
                "reranker_model_name": cfg.ask.reranker,
            },
            "llm": cfg.ask_llm.to_mmore(),
            "system_prompt": RAG_PROMPT,
        },
        RAGConfig,
    )

    graph = approver = None
    privacy_path = cfg.privacy.rag_privacy_config
    if privacy and privacy_path:
        graph, approver, _ = setup_privacy(
            _privacy_config(str(privacy_path), review), interactive_ok=review
        )
    elif privacy:
        log.info("No rag_privacy_config set. Answering without privacy mode.")

    from pymilvus.exceptions import MilvusException

    from chitchat.stages.index import milvus_error

    try:
        rag = RAGPipeline.from_config(rag_config, privacy_graph=graph, privacy_approver=approver)
        query = {"input": question, "collection_name": cfg.index.collection}
        out = rag(query, return_dict=True)[0]
    except MilvusException as e:
        raise milvus_error(cfg.index.db_uri, e) from None
    except ValueError as e:
        if "collection" not in str(e):
            raise
        raise StageError(
            f"No index called {cfg.index.collection!r} yet. Run the index stage first."
        ) from None
    result = format_result(question, out, sources)
    append_jsonl(run.answers, result)
    return result


def _source_line(s: dict[str, Any]) -> str:
    where = f"https://doi.org/{s['doi']}" if s.get("doi") else (s.get("url") or "")
    year = f" ({s['year']})" if s.get("year") else ""
    note = "" if s["known"] else "  (unknown tag)"
    return f"  [{s['tag']}] {s.get('title') or ''}{year} {where}{note}".rstrip()


def render(result: dict[str, Any]) -> str:
    lines = [result["answer"], ""]
    if result["sources"]:
        lines.append("Sources:")
        lines += [_source_line(s) for s in result["sources"]]
    elif result["retrieved"] and not result["aborted"]:
        # The model sometimes forgets to cite. Show what it was given, labelled as such.
        lines.append("Sources (retrieved, not cited by the model):")
        lines += [_source_line(s) for s in result["retrieved"]]
    elif not result["aborted"]:
        lines.append("No sources: nothing was retrieved.")
    summary = result["privacy_report_summary"]
    sent = (summary or {}).get("sanitized_query")
    if sent and sent.strip() != result["question"].strip():
        lines += ["", f"Note: privacy mode sent your question as: {sent}"]
        lines.append("If a name was masked by mistake, rephrase it or use --no-privacy.")
    if summary:
        lines += [
            "",
            f"Privacy: {summary['outcome']} · question: {_masked(summary, 'question')} · "
            f"context: {_masked(summary, 'context')}",
        ]
    return "\n".join(lines)


def _masked(summary: dict[str, Any], where: str) -> str:
    """`2 masked (PERSON 1, EMAIL_ADDRESS 1)`, or `nothing masked`."""
    if where == "question":
        count, entities = summary.get("question_masked", 0), summary.get("question_entities")
    else:
        count, entities = summary.get("spans_masked", 0), summary.get("entities")
    if not count:
        return "nothing masked"
    kinds = ", ".join(f"{k} {v}" for k, v in (entities or {}).items())
    return f"{count} masked ({kinds})" if kinds else f"{count} masked"
