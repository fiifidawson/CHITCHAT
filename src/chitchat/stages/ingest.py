"""Stage 2: read the user's own documents with mmore process.

Own documents are never screened. They go to sanitize, then to the index.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from chitchat.config import PipelineConfig
from chitchat.ids import doc_id
from chitchat.jsonl import read_jsonl, write_jsonl
from chitchat.run_dir import RunDir

log = logging.getLogger(__name__)


def to_doc_records(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Give each mmore sample a stable doc_id. A file with several samples gets `#2`, `#3`..."""
    records: list[dict[str, Any]] = []
    seen: dict[str, int] = {}
    for sample in samples:
        metadata = sample.get("metadata") or {}
        file_path = metadata.get("file_path", "")
        base_id = doc_id(Path(file_path))
        seen[base_id] = seen.get(base_id, 0) + 1
        did = base_id if seen[base_id] == 1 else f"{base_id}#{seen[base_id]}"
        records.append({"doc_id": did, "text": sample.get("text") or "", "metadata": metadata})
    return records


def run_ingest(cfg: PipelineConfig, run: RunDir) -> int:
    folder = cfg.own_documents.folder
    if not folder or not folder.is_dir():
        from chitchat import ui

        ui.note(f"No own documents folder ({ui.shorten_path(folder or '')}). Skipped.")
        return 0

    from mmore.run_process import merged_results_path, process

    from chitchat.stages.discover import quiet_mupdf

    quiet_mupdf()

    out = run.docs_process
    process_config = {
        "data_path": str(folder),
        "google_drive_ids": [],
        "dispatcher_config": {
            "output_path": str(out),
            "use_fast_processors": cfg.own_documents.fast,
            "distributed": False,
            "extract_images": False,
            "fail_on_error": False,
        },
    }
    config_path = run.raw / "process_config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(yaml.safe_dump(process_config), encoding="utf-8")

    process(str(config_path))
    samples = list(read_jsonl(Path(merged_results_path(str(out)))))
    n = write_jsonl(run.docs_raw, to_doc_records(samples))
    from chitchat import ui

    ui.print_box(
        "Own documents",
        [("Documents", n, f"read from {ui.shorten_path(folder)}")],
        footer=f"Saved to {ui.shorten_path(run.docs_raw)}. They are never screened.",
    )
    return n
