"""The search plan: concepts with synonyms, grouped into categories.

A category becomes one boolean query: an AND of OR-groups, one OR-group per concept.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from chitchat.config import SearchPreset

# OpenAlex rejects longer searches unless you pay for an API key.
OPENALEX_MAX_CHARS = 1500


class PlanError(ValueError):
    """A drafted plan that can't be used."""


# --- What the LLM returns -----------------------------------------------------------


class Concept(BaseModel):
    word: str = Field(description="The concept, as a short phrase that appears in papers.")
    synonyms: list[str] = Field(
        description="Other phrases for the same concept, most important first. No duplicates."
    )


class Category(BaseModel):
    name: str = Field(description="A short title for this angle of the question.")
    words: list[str] = Field(
        description="The concept words this category combines with AND. Use words from concepts."
    )


class SearchPlan(BaseModel):
    concepts: list[Concept]
    categories: list[Category]
    rationale: str = Field(
        description=(
            "Name each key idea of the question and the concept that covers it. "
            "One or two sentences."
        )
    )


class ClarifyingQuestion(BaseModel):
    question: str
    suggestions: list[str] = Field(description="Two to four short possible answers.")


class ClarifyingQuestions(BaseModel):
    questions: list[ClarifyingQuestion]


# --- Cleaning and checking ---------------------------------------------------------------

_SPACES = re.compile(r"\s+")
_BAD_CHARS = re.compile(r'["()]|\b(?:AND|OR|NOT)\b')


def _clean_term(term: str) -> str:
    """No quotes, brackets or boolean operators inside a term."""
    return _SPACES.sub(" ", _BAD_CHARS.sub(" ", term)).strip(" ,;.")


def plan_problems(plan: SearchPlan, preset: SearchPreset) -> list[str]:
    """Rule breaks in a raw draft, phrased so the LLM can fix them."""
    problems: list[str] = []
    known = {_clean_term(c.word).lower() for c in plan.concepts}
    for cat in plan.categories:
        words = {_clean_term(w).lower() for w in cat.words}
        unknown = sorted(w for w in words if w not in known)
        if unknown:
            problems.append(
                f"category '{cat.name}' uses {', '.join(repr(w) for w in unknown)}, which are not "
                "concept words. Use concept words only; put synonyms inside their concept."
            )
        if len(words & known) < 2:
            problems.append(
                f"category '{cat.name}' combines fewer than 2 concepts. Combine at least 2."
            )
    if len(plan.categories) < preset.min_categories:
        problems.append(f"make at least {preset.min_categories} categories")
    return problems


def normalize_plan(plan: SearchPlan, preset: SearchPreset) -> tuple[SearchPlan, list[str]]:
    """Clean terms, drop duplicates and unknown words, and apply the preset's limits.

    Returns the cleaned plan and plain-language notes on what was changed.
    """
    notes: list[str] = []
    concepts: list[Concept] = []
    seen: set[str] = set()
    for c in plan.concepts:
        word = _clean_term(c.word)
        if not word or word.lower() in seen:
            continue
        seen.add(word.lower())
        synonyms: list[str] = []
        taken = {word.lower()}
        for s in c.synonyms:
            term = _clean_term(s)
            if term and term.lower() not in taken:
                taken.add(term.lower())
                synonyms.append(term)
        if len(synonyms) > preset.max_synonyms:
            notes.append(f"kept the first {preset.max_synonyms} synonyms of '{word}'")
            synonyms = synonyms[: preset.max_synonyms]
        concepts.append(Concept(word=word, synonyms=synonyms))

    known = {c.word.lower(): c.word for c in concepts}
    categories: list[Category] = []
    for cat in plan.categories:
        words: list[str] = []
        for w in cat.words:
            match = known.get(_clean_term(w).lower())
            if match is None:
                notes.append(f"dropped unknown concept '{w}' from '{cat.name}'")
            elif match not in words:
                words.append(match)
        if len(words) > preset.max_concepts_per_category:
            notes.append(
                f"kept the first {preset.max_concepts_per_category} concepts of '{cat.name}'"
            )
            words = words[: preset.max_concepts_per_category]
        if words:
            categories.append(Category(name=cat.name.strip() or "Search", words=words))

    if len(categories) > preset.max_categories:
        notes.append(f"kept the first {preset.max_categories} categories")
        categories = categories[: preset.max_categories]
    if not categories:
        raise PlanError("The draft has no usable categories. Try rephrasing the question.")

    used = {w for cat in categories for w in cat.words}
    concepts = [c for c in concepts if c.word in used]
    return SearchPlan(concepts=concepts, categories=categories, rationale=plan.rationale), notes


# --- Queries and the OpenAlex limit ---------------------------------------------------------


def build_queries(plan: SearchPlan) -> list[dict[str, str]]:
    """The boolean query per category, exactly as mmore builds it."""
    from mmore.paper_discovery.boolean import build_boolean_queries
    from mmore.paper_discovery.schema import SynonymEntry

    entries = [SynonymEntry(word=c.word, synonyms=list(c.synonyms)) for c in plan.concepts]
    categories = {cat.name: list(cat.words) for cat in plan.categories}
    return [
        {"category": q.combination_title, "query": q.boolean_combination}
        for q in build_boolean_queries(entries, categories)
    ]


def fit_to_limit(plan: SearchPlan, limit: int = OPENALEX_MAX_CHARS) -> tuple[SearchPlan, list[str]]:
    """Drop the last synonyms of the longest groups until every query fits `limit` characters.

    Deterministic. Returns the fitted plan and what was dropped.
    """
    concepts = {c.word: list(c.synonyms) for c in plan.concepts}
    dropped: list[str] = []

    def current() -> SearchPlan:
        return SearchPlan(
            concepts=[Concept(word=w, synonyms=s) for w, s in concepts.items()],
            categories=plan.categories,
            rationale=plan.rationale,
        )

    while True:
        too_long = [q for q in build_queries(current()) if len(q["query"]) > limit]
        if not too_long:
            break
        worst = max(too_long, key=lambda q: len(q["query"]))
        category = next(c for c in plan.categories if c.name == worst["category"])
        candidates = [w for w in category.words if concepts[w]]
        if not candidates:
            raise PlanError(
                f"'{category.name}' is still over {limit} characters with no synonyms left. "
                "Ask for fewer or shorter concepts."
            )
        word = max(candidates, key=lambda w: (len(concepts[w]), sum(map(len, concepts[w]))))
        dropped.append(f"'{concepts[word].pop()}' from '{word}'")
    return current(), dropped


# --- Files for mmore --------------------------------------------------------------------------


def write_plan_files(search_dir: Path, plan: SearchPlan, preset: SearchPreset) -> Path:
    """Write synonyms.jsonl, categories.yaml and discovery.yaml. Returns the discovery config."""
    search_dir.mkdir(parents=True, exist_ok=True)
    with open(search_dir / "synonyms.jsonl", "w", encoding="utf-8", newline="\n") as f:
        for c in plan.concepts:
            f.write(json.dumps({"word": c.word, "synonyms": c.synonyms}, ensure_ascii=False) + "\n")
    categories = {"categories": {cat.name: cat.words for cat in plan.categories}}
    (search_dir / "categories.yaml").write_text(
        yaml.safe_dump(categories, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    discovery: dict[str, Any] = {
        "synonyms_path": "synonyms.jsonl",
        "categories_path": "categories.yaml",
        "output_file": "papers.jsonl",
        "sources": list(preset.sources),
        "max_pages": preset.max_pages,
        "max_results": preset.max_results,
        "download_pdfs": preset.download_pdfs,
        "pdf_dir": "pdfs",
        "pdf_extractor": "fast",
        "pdf_timeout": 30,
        "force_redownload": False,
        "arxiv_enable_pair_query": True,
    }
    path = search_dir / "discovery.yaml"
    header = "# Written by `chitchat search`. Paths are relative to this file.\n"
    path.write_text(header + yaml.safe_dump(discovery, sort_keys=False), encoding="utf-8")
    return path
