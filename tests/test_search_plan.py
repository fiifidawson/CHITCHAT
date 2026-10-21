from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
import yaml

from chitchat.config import DEFAULT_PRESETS, SearchPreset, load_pipeline_config
from chitchat.search.plan import (
    OPENALEX_MAX_CHARS,
    Category,
    Concept,
    PlanError,
    SearchPlan,
    build_queries,
    fit_to_limit,
    normalize_plan,
    plan_problems,
    write_plan_files,
)
from chitchat.search.session import (
    collection_name,
    new_run_folder,
    slugify,
    write_run_config,
)

DEEP = SearchPreset(**DEFAULT_PRESETS["deep"])
SHALLOW = SearchPreset(**DEFAULT_PRESETS["shallow"])


def _plan(n_synonyms: int = 3, n_categories: int = 2) -> SearchPlan:
    concepts = [
        Concept(word=f"concept {i}", synonyms=[f"synonym {i}.{j}" for j in range(n_synonyms)])
        for i in range(4)
    ]
    categories = [
        Category(name=f"Angle {k}", words=["concept 0", f"concept {k + 1}"])
        for k in range(n_categories)
    ]
    return SearchPlan(concepts=concepts, categories=categories, rationale="r")


# --- normalize_plan ------------------------------------------------------------------------


def test_normalize_cleans_terms_and_drops_duplicates() -> None:
    raw = SearchPlan(
        concepts=[
            Concept(
                word='"Consent"', synonyms=["consent", "informed consent", "(opt-out)", "AND", ""]
            ),
            Concept(word="LLM data", synonyms=["training data", "Training Data"]),
            Concept(word="consent", synonyms=["duplicate concept"]),
        ],
        categories=[Category(name="Main", words=["Consent", "llm data", "unknown"])],
        rationale="why",
    )
    plan, notes = normalize_plan(raw, DEEP)
    assert [c.word for c in plan.concepts] == ["Consent", "LLM data"]
    assert plan.concepts[0].synonyms == ["informed consent", "opt-out"]
    assert plan.concepts[1].synonyms == ["training data"]
    assert plan.categories[0].words == ["Consent", "LLM data"]
    assert any("unknown" in n for n in notes)


def test_normalize_applies_preset_limits() -> None:
    plan, notes = normalize_plan(_plan(n_synonyms=9, n_categories=3), SHALLOW)
    assert len(plan.categories) == SHALLOW.max_categories == 1
    assert all(len(c.synonyms) <= SHALLOW.max_synonyms for c in plan.concepts)
    assert {c.word for c in plan.concepts} == {"concept 0", "concept 1"}  # unused concepts dropped
    assert notes


def test_normalize_needs_a_category() -> None:
    raw = SearchPlan(
        concepts=[Concept(word="a", synonyms=[])],
        categories=[Category(name="x", words=["nope"])],
        rationale="",
    )
    with pytest.raises(PlanError, match="no usable categories"):
        normalize_plan(raw, DEEP)


# --- queries and the OpenAlex limit ------------------------------------------------------


def test_build_queries_is_and_of_ors() -> None:
    queries = build_queries(_plan(n_synonyms=1, n_categories=1))
    assert queries == [
        {
            "category": "Angle 0",
            "query": '("concept 0" OR "synonym 0.0") AND ("concept 1" OR "synonym 1.0")',
        }
    ]


def test_fit_to_limit_is_deterministic_and_fits() -> None:
    long = SearchPlan(
        concepts=[
            Concept(
                word=f"c{i}", synonyms=[f"a fairly long synonym phrase {i}-{j}" for j in range(40)]
            )
            for i in range(3)
        ],
        categories=[Category(name="All", words=["c0", "c1", "c2"])],
        rationale="",
    )
    first, dropped = fit_to_limit(long)
    second, _ = fit_to_limit(long)
    assert first == second
    assert dropped
    assert all(len(q["query"]) <= OPENALEX_MAX_CHARS for q in build_queries(first))
    # The most important synonyms (listed first) are kept.
    assert first.concepts[0].synonyms[0] == "a fairly long synonym phrase 0-0"


def test_fit_to_limit_leaves_short_plans_alone() -> None:
    plan = _plan()
    fitted, dropped = fit_to_limit(plan)
    assert fitted.concepts == plan.concepts and dropped == []


def test_fit_to_limit_gives_up_clearly() -> None:
    huge = SearchPlan(
        concepts=[Concept(word="x" * 800, synonyms=[]), Concept(word="y" * 800, synonyms=[])],
        categories=[Category(name="Too big", words=["x" * 800, "y" * 800])],
        rationale="",
    )
    with pytest.raises(PlanError, match="Too big"):
        fit_to_limit(huge)


# --- files -------------------------------------------------------------------------------------


def test_plan_files_load_in_mmore(tmp_path: Path) -> None:
    pytest.importorskip("mmore.paper_discovery")
    from mmore.paper_discovery import PaperDiscoveryConfig
    from mmore.paper_discovery.boolean import build_boolean_queries, load_synonyms
    from mmore.utils import load_config

    plan = _plan()
    discovery = write_plan_files(tmp_path / "search", plan, SHALLOW)
    cfg = load_config(str(discovery), PaperDiscoveryConfig)
    assert cfg.max_results == SHALLOW.max_results and cfg.download_pdfs is False
    synonyms = load_synonyms(discovery.parent / cfg.synonyms_path)
    categories = yaml.safe_load(
        (discovery.parent / cfg.categories_path).read_text(encoding="utf-8")
    )
    rebuilt = build_boolean_queries(synonyms, categories["categories"])
    assert [q.boolean_combination for q in rebuilt] == [q["query"] for q in build_queries(plan)]


@pytest.mark.parametrize(
    ("platform", "expected"),
    [("linux", "lite"), ("win32", "http://127.0.0.1:19530")],
)
def test_run_config_milvus_per_platform(
    project: Path, monkeypatch: pytest.MonkeyPatch, platform: str, expected: str
) -> None:
    from chitchat.search import session

    monkeypatch.setattr(session.sys, "platform", platform)
    template = project / "pipeline.yaml"  # uses a Milvus Lite file
    cfg = load_pipeline_config(template)
    run_root = project / "runs" / "r"
    discovery = write_plan_files(run_root / "search", _plan(), SHALLOW)
    run_cfg = load_pipeline_config(write_run_config(template, cfg, run_root, discovery, "deep"))
    if expected == "lite":
        assert run_cfg.index.db_uri == str(run_root.resolve() / "milvus.db")
    else:
        assert run_cfg.index.db_uri == expected


def test_run_config_points_at_the_run(project: Path) -> None:
    template = project / "pipeline.yaml"
    cfg = load_pipeline_config(template)
    run_root = project / "runs" / "consent-llm-data-2026-10-21"
    discovery = write_plan_files(run_root / "search", _plan(), SHALLOW)

    path = write_run_config(template, cfg, run_root, discovery, mode="shallow")
    run_cfg = load_pipeline_config(path)
    assert run_cfg.run_root == run_root.resolve()
    assert run_cfg.discovery.config == discovery.resolve()
    assert run_cfg.privacy.sanitize_config == cfg.privacy.sanitize_config
    assert run_cfg.screening.criteria == cfg.screening.criteria
    assert run_cfg.index.collection == collection_name(run_root.name)
    assert run_cfg.search.mode == "shallow"
    assert run_cfg.screening.min_chars <= 300  # shallow screens abstracts


# --- run folders --------------------------------------------------------------------------------


def test_slugify() -> None:
    assert (
        slugify("How do NGOs get consent for LLM training data?")
        == "ngos-get-consent-llm-training-data"
    )
    assert slugify("???") == "search"


def test_new_run_folder(tmp_path: Path) -> None:
    day = date(2026, 10, 21)
    first = new_run_folder(tmp_path, "Consent in LLM data", today=day)
    assert first.name == "consent-llm-data-2026-10-21"
    first.mkdir()
    assert new_run_folder(tmp_path, "Consent in LLM data", today=day).name.endswith("-2")
    assert new_run_folder(tmp_path, None, run_name="my-run").name == "my-run"
    with pytest.raises(ValueError, match="run-name"):
        new_run_folder(tmp_path, None, run_name="bad name!")


def test_collection_name() -> None:
    assert collection_name("consent-llm-2026-10-21") == "run_consent_llm_2026_10_21"


def test_plan_problems() -> None:
    bad = SearchPlan(
        concepts=[
            Concept(word="consent", synonyms=["informed consent"]),
            Concept(word="LLMs", synonyms=[]),
        ],
        categories=[
            Category(name="Synonyms as words", words=["consent", "informed consent"]),
            Category(name="Good", words=["consent", "LLMs"]),
        ],
        rationale="",
    )
    problems = plan_problems(bad, DEEP)
    assert any("'informed consent'" in p and "not concept words" in p for p in problems)
    assert any("'Synonyms as words'" in p and "fewer than 2" in p for p in problems)
    assert any("at least 3 categories" in p for p in problems)
    assert plan_problems(_plan(), SHALLOW) == []
