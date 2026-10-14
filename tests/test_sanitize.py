from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from chitchat.config import ConfigError
from chitchat.stages.sanitize import (
    OWN_DOCUMENTS,
    PAPERS,
    Sanitizer,
    load_sanitize_configs,
    sanitize_papers,
    split_text,
    unglue_emails,
)

REPO = Path(__file__).resolve().parents[1]
NAMES = re.compile(r"Alice Smith|Bob Jones")


# --- Fakes: no Presidio. Spans are found with a regex; masking is mmore's real strategy. ---


def _policy():
    from mmore.privacy.schemas.policy import PrivacyPolicy

    return PrivacyPolicy(
        domain="global",
        sensitive_entities=["PERSON"],
        detection_engine="presidio",
        sanitization_strategy="token_masking",
        consistency=True,
        domain_prompt="",
    )


class FakeAnalyzer:
    def build_policy(self, query, chunks):
        return _policy()


class FakeDetector:
    def detect(self, policy, chunks):
        from mmore.privacy.detection.base import PIISpan

        spans = [
            [PIISpan(m.start(), m.end(), "PERSON", 0.99) for m in NAMES.finditer(c)] for c in chunks
        ]
        count = sum(len(s) for s in spans)
        risk = SimpleNamespace(count=count, entity_counts={"PERSON": count}, level="low")
        return spans, risk


class FakeSanitizerAgent:
    def sanitize(self, policy, chunks, spans):
        from mmore.privacy.sanitization.token_masking_strategy import TokenMaskingStrategy

        return TokenMaskingStrategy().apply(chunks, spans, policy)


@pytest.fixture
def sanitizer() -> Sanitizer:
    pytest.importorskip("mmore.privacy")
    return Sanitizer(FakeAnalyzer(), FakeDetector(), FakeSanitizerAgent())


# --- Tests ---


def test_split_text_round_trips() -> None:
    text = "\n\n".join(f"Paragraph {i} " + "x" * 900 for i in range(20))
    parts = split_text(text, size=5000)
    assert len(parts) > 1
    assert all(len(p) <= 5000 for p in parts)
    assert "".join(parts) == text


def test_split_text_huge_paragraph() -> None:
    text = "y" * 12_000
    parts = split_text(text, size=5000)
    assert [len(p) for p in parts] == [5000, 5000, 2000]
    assert "".join(parts) == text


def test_consistent_tokens_within_one_document(sanitizer: Sanitizer) -> None:
    abstract = "Alice Smith wrote this."
    text = "Alice Smith and Bob Jones met. Later Alice Smith left."
    (clean_abstract, clean_text), report = sanitizer.sanitize([abstract, text])
    assert "Alice" not in clean_abstract + clean_text
    assert clean_abstract == "[PERSON_1] wrote this."
    assert clean_text == "[PERSON_1] and [PERSON_2] met. Later [PERSON_1] left."
    assert report == {"count": 4, "entities": {"PERSON": 4}, "level": "low"}


def test_consistency_across_split_parts(sanitizer: Sanitizer) -> None:
    text = "Alice Smith." + "\n\n" + "z" * 6000 + "\n\n" + "Alice Smith again."
    (clean,), _ = sanitizer.sanitize([text])
    assert clean.count("[PERSON_1]") == 2


def test_empty_and_none_pass_through(sanitizer: Sanitizer) -> None:
    out, report = sanitizer.sanitize([None, ""])
    assert out == [None, ""]
    assert report["count"] == 0


def test_sanitize_papers_adds_id_and_report(sanitizer: Sanitizer) -> None:
    papers = [{"title": "T", "doi": "10.1/x", "abstract": "By Bob Jones.", "extracted_text": None}]
    [out] = sanitize_papers(papers, sanitizer)
    assert out["paper_id"] == "doi:10.1/x"
    assert out["abstract"] == "By [PERSON_1]."
    assert out["extracted_text"] is None
    assert "Bob" not in str(out["privacy"])


def test_two_entity_lists() -> None:
    configs = load_sanitize_configs(REPO / "configs" / "sanitize.yaml")
    papers = configs[PAPERS]["detection"]["entity_types"]
    docs = configs[OWN_DOCUMENTS]["detection"]["entity_types"]
    assert "LOCATION" not in papers and "DATE_TIME" not in papers
    assert {"LOCATION", "DATE_TIME", "PERSON"} <= set(docs)
    assert "entity_types_papers" not in configs[PAPERS]["detection"]


def test_mmore_accepts_both_configs() -> None:
    pytest.importorskip("mmore.privacy")
    from mmore.privacy.config import PrivacyConfig
    from mmore.utils import load_config

    for config in load_sanitize_configs(REPO / "configs" / "sanitize.yaml").values():
        cfg = load_config(config, PrivacyConfig)
        assert cfg.detection.entity_types


@pytest.mark.parametrize(
    "missing",
    ["domain", "engine", "entity_types_own_documents", "confidence_threshold_own_documents"],
)
def test_unpinned_config_is_refused(tmp_path: Path, missing: str) -> None:
    data = yaml.safe_load((REPO / "configs" / "sanitize.yaml").read_text(encoding="utf-8"))
    if missing == "domain":
        del data["domain"]
    else:
        del data["detection"][missing]
    path = tmp_path / "sanitize.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(ConfigError, match=missing):
        load_sanitize_configs(path)


def test_thresholds_per_list() -> None:
    """Presidio scores phone numbers at 0.4: own documents must go that low to mask them."""
    configs = load_sanitize_configs(REPO / "configs" / "sanitize.yaml")
    assert configs[PAPERS]["detection"]["confidence_threshold"] == 0.7
    assert configs[OWN_DOCUMENTS]["detection"]["confidence_threshold"] == 0.4
    assert "confidence_threshold_papers" not in configs[PAPERS]["detection"]


def test_shared_threshold_still_works(tmp_path: Path) -> None:
    data = yaml.safe_load((REPO / "configs" / "sanitize.yaml").read_text(encoding="utf-8"))
    for kind in ("papers", "own_documents"):
        del data["detection"][f"confidence_threshold_{kind}"]
    data["detection"]["confidence_threshold"] = 0.5
    path = tmp_path / "sanitize.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    configs = load_sanitize_configs(path)
    assert {c["detection"]["confidence_threshold"] for c in configs.values()} == {0.5}


def test_rag_privacy_masks_phone_numbers() -> None:
    data = yaml.safe_load((REPO / "configs" / "rag_privacy.yaml").read_text(encoding="utf-8"))
    assert data["detection"]["confidence_threshold"] <= 0.4
    assert "PHONE_NUMBER" in data["detection"]["entity_types"]


def test_unglue_emails() -> None:
    assert (
        unglue_emails("Email: email@email.com2\nAbstract") == "Email: email@email.com 2\nAbstract"
    )
    assert unglue_emails("write to a.b@uni-x.ac.uk12.") == "write to a.b@uni-x.ac.uk 12."
    assert unglue_emails("a.b@uni.edu and 10.1234/x2") == "a.b@uni.edu and 10.1234/x2"
