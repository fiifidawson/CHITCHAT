"""`chitchat search`: plan a search with the user, then set up a run folder for it."""

from __future__ import annotations

import os
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Protocol

import yaml

from chitchat.config import DOCKER_MILVUS, PipelineConfig, SearchPreset
from chitchat.jsonl import write_json
from chitchat.run_dir import RunDir
from chitchat.search.drafting import Drafter, add_feedback, add_repair, first_messages
from chitchat.search.plan import (
    OPENALEX_MAX_CHARS,
    SearchPlan,
    build_queries,
    fit_to_limit,
    normalize_plan,
    plan_problems,
    write_plan_files,
)

REPAIR_ATTEMPTS = 2  # automatic fixes of a draft that breaks the rules

_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "does", "for", "from", "how",
    "in", "into", "is", "it", "of", "on", "or", "the", "their", "to", "what", "when", "which",
    "who", "why", "with",
}  # fmt: skip


# --- Run folders -------------------------------------------------------------------------------


def slugify(text: str, max_words: int = 6, max_chars: int = 50) -> str:
    """`How do NGOs get consent for LLM data?` -> `ngos-get-consent-llm-data`."""
    words = [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in _STOPWORDS]
    slug = "-".join(words[:max_words])[:max_chars].strip("-")
    return slug or "search"


def new_run_folder(
    runs_dir: Path, question: str | None, run_name: str | None = None, today: date | None = None
) -> Path:
    """A folder that doesn't exist yet: `<slug>-<date>`, then `-2`, `-3`… if taken."""
    if run_name:
        if not re.fullmatch(r"[A-Za-z0-9._-]+", run_name):
            raise ValueError("--run-name may only use letters, digits, '.', '_' and '-'")
        base = run_name
    else:
        base = f"{slugify(question or 'predefined')}-{(today or date.today()).isoformat()}"
    candidate, n = runs_dir / base, 2
    while candidate.exists():
        candidate, n = runs_dir / f"{base}-{n}", n + 1
    return candidate


def _relative(path: Path, start: Path) -> str:
    try:
        return Path(os.path.relpath(path, start)).as_posix()
    except ValueError:  # different drive on Windows
        return path.as_posix()


def collection_name(run_name: str) -> str:
    """A Milvus collection name for this run: letters, digits and underscores."""
    return ("run_" + re.sub(r"[^A-Za-z0-9_]", "_", run_name))[:200]


def write_run_config(
    template_path: Path,
    cfg: PipelineConfig,
    run_root: Path,
    discovery_config: Path,
    mode: str | None,
) -> Path:
    """Write `<run>/pipeline.yaml`: the template's settings, pointed at this run.

    Paths are relative to the run folder, and the run gets its own Milvus collection.
    """
    data: dict[str, Any] = yaml.safe_load(template_path.read_text(encoding="utf-8")) or {}
    data["run_name"] = run_root.name
    data["runs_dir"] = _relative(run_root.parent, run_root)
    data["discovery"] = {"config": _relative(discovery_config, run_root)}
    privacy = data.setdefault("privacy", {})
    privacy["sanitize_config"] = _relative(cfg.privacy.sanitize_config, run_root)
    if cfg.privacy.rag_privacy_config:
        privacy["rag_privacy_config"] = _relative(cfg.privacy.rag_privacy_config, run_root)
    screening = data.setdefault("screening", {})
    screening["criteria"] = _relative(cfg.screening.criteria, run_root)
    if cfg.own_documents.folder:
        data.setdefault("own_documents", {})["folder"] = _relative(
            cfg.own_documents.folder, run_root
        )
    index = data.setdefault("index", {})
    if index.get("db_uri", "auto") == "auto":
        index["db_uri"] = "auto"  # Docker on Windows, a file in this folder elsewhere
    elif "://" not in cfg.index.db_uri:
        # Milvus Lite (a local file) has no Windows build: use Milvus in Docker there.
        index["db_uri"] = DOCKER_MILVUS if sys.platform == "win32" else "milvus.db"
    index["collection"] = collection_name(run_root.name)
    if mode:
        data.setdefault("search", {})["mode"] = mode
        if mode == "shallow":
            # Shallow runs screen abstracts. Most are 500-2,000 characters.
            screening["min_chars"] = min(int(screening.get("min_chars", 500)), 300)

    run_root.mkdir(parents=True, exist_ok=True)
    path = RunDir(run_root).config
    header = (
        f"# Written by `chitchat search` on {datetime.now():%Y-%m-%d %H:%M}.\n"
        "# Paths are relative to this folder. Use it with: chitchat <command> -c <this file>\n"
    )
    path.write_text(header + yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


# --- Talking to the user --------------------------------------------------------------------


class SearchIO(Protocol):
    def show(self, renderable: Any) -> None: ...
    def ask(self, prompt: str) -> str: ...
    def choose(self, prompt: str, choices: list[str], default: str) -> str: ...


class ConsoleIO:
    """The real terminal, with rich prompts."""

    def show(self, renderable: Any) -> None:
        from chitchat import ui

        ui.console.print(renderable)

    def ask(self, prompt: str) -> str:
        from rich.prompt import Prompt

        from chitchat import ui

        return Prompt.ask(prompt, default="", show_default=False, console=ui.console)

    def choose(self, prompt: str, choices: list[str], default: str) -> str:
        from rich.prompt import Prompt

        from chitchat import ui

        return Prompt.ask(prompt, choices=choices, default=default, console=ui.console)


# --- The planning session ---------------------------------------------------------------------


@dataclass
class PlanResult:
    plan: SearchPlan
    queries: list[dict[str, str]]
    log: dict[str, Any] = field(default_factory=dict)


def _answer_from(raw: str, suggestions: list[str]) -> str:
    """`2` or `1,3` picks suggestions; anything else is a free answer."""
    picks = [p.strip() for p in raw.split(",")]
    if raw.strip() and all(p.isdigit() and 1 <= int(p) <= len(suggestions) for p in picks):
        return "; ".join(suggestions[int(p) - 1] for p in picks)
    return raw.strip()


def _show_draft(
    io: SearchIO,
    plan: SearchPlan,
    queries: list[dict[str, str]],
    notes: list[str],
    sources: list[str],
) -> None:
    from rich.text import Text

    from chitchat import ui

    synonyms = {c.word: c.synonyms for c in plan.concepts}
    lengths = {q["category"]: len(q["query"]) for q in queries}
    categories = [
        (cat.name, [(w, synonyms.get(w, [])) for w in cat.words], lengths.get(cat.name, 0))
        for cat in plan.categories
    ]
    limit = OPENALEX_MAX_CHARS if "openalex" in sources else None
    io.show(ui.draft_view(categories, limit, sources))
    if plan.rationale:
        io.show(Text(plan.rationale, style="dim"))
    for line in notes:
        io.show(Text(f"· {line}", style="dim"))


def plan_search(
    question: str,
    mode: str,
    preset: SearchPreset,
    drafter: Drafter,
    io: SearchIO,
    mask: Callable[[str], str] = lambda text: text,
    auto_accept: bool = False,
) -> PlanResult | None:
    """Clarify (deep only), draft, then accept / change / quit. Returns None on quit."""
    from rich.text import Text

    from chitchat import ui

    log: dict[str, Any] = {"question": question, "mode": mode, "clarifying": [], "turns": []}
    sent = mask(question)
    if sent != question:
        io.show(Text(f"⚠ Personal data was masked before sending: {sent}", style=ui.ACCENT))
    log["question_sent"] = sent

    answers: list[tuple[str, str]] = []
    if preset.clarifying_questions and not auto_accept:
        io.show(Text("A few questions to focus the search. Press Enter to skip one.", style="bold"))
        for q in drafter.clarify(sent, preset.clarifying_questions).questions:
            options = "  ".join(f"[{i}] {s}" for i, s in enumerate(q.suggestions, 1))
            io.show(Text(f"\n{q.question}", style=f"bold {ui.ACCENT}"))
            if options:
                io.show(Text(f"  {options}", style="dim"))
            answer = mask(
                _answer_from(io.ask("  Your answer (number, text or Enter)"), q.suggestions)
            )
            answers.append((q.question, answer))
            log["clarifying"].append(
                {"question": q.question, "suggestions": q.suggestions, "answer": answer}
            )

    messages = first_messages(sent, answers, preset)
    while True:
        with ui.console.status("Drafting the search…", spinner_style=ui.ACCENT):
            raw = drafter.plan(messages)
            # Let the LLM fix rule breaks itself before the user sees the draft.
            for _ in range(REPAIR_ATTEMPTS):
                problems = plan_problems(raw, preset)
                if not problems:
                    break
                messages = add_repair(messages, raw, problems)
                raw = drafter.plan(messages)
        plan, notes = normalize_plan(raw, preset)
        dropped: list[str] = []
        if "openalex" in preset.sources:  # only OpenAlex limits the query length
            plan, dropped = fit_to_limit(plan)
        if dropped:
            notes.append(
                f"dropped {len(dropped)} synonyms so every query fits OpenAlex's "
                f"{OPENALEX_MAX_CHARS:,}-character limit: {', '.join(dropped)}"
            )
        queries = build_queries(plan)
        turn: dict[str, Any] = {"draft": plan.model_dump(), "notes": notes}
        log["turns"].append(turn)
        _show_draft(io, plan, queries, notes, preset.sources)

        feedback = ""
        while not feedback:
            if auto_accept:
                choice = "a"
            else:
                io.show(Text("[a] accept   [c] ask for changes   [q] quit", style="bold"))
                choice = io.choose("Your choice", ["a", "c", "q"], default="a")
            if choice == "a":
                log["accepted"] = plan.model_dump()
                return PlanResult(plan=plan, queries=queries, log=log)
            if choice == "q":
                return None
            feedback = mask(io.ask("What should change?").strip())
        turn["feedback"] = feedback
        # Revise from the draft the user saw, not the LLM's raw output.
        messages = add_feedback(messages, plan, feedback)


def save_plan(run: RunDir, result: PlanResult, preset: SearchPreset) -> Path:
    """Write the plan files and the full conversation. Returns the discovery config."""
    discovery = write_plan_files(run.search, result.plan, preset)
    write_json(run.plan, {**result.log, "saved": datetime.now().isoformat(timespec="seconds")})
    return discovery


def question_masker(rag_privacy_config: Path | None) -> Callable[[str], str]:
    """Mask personal data with the local Presidio check from rag_privacy.yaml. No LLM."""
    if not rag_privacy_config:
        return lambda text: text
    from chitchat.stages.sanitize import Sanitizer

    config = yaml.safe_load(rag_privacy_config.read_text(encoding="utf-8"))
    sanitizer: Sanitizer | None = None

    def mask(text: str) -> str:
        nonlocal sanitizer
        if not text.strip():
            return text
        if sanitizer is None:
            sanitizer = Sanitizer.from_dict(config)
        (clean,), _ = sanitizer.sanitize([text])
        return clean or text

    return mask
