# CHITCHAT — Open-Source Readiness Plan

Target standard: [LiGHT GitHub Repository Checklist](https://lighters-playground.github.io/LiGHT-doc/checklist/) (18 items + 8 reader questions).

Audit date: 2026-07-27 · Branch: `v2` · Tracked files: 42 · Commits: 54 · Contributors: 3

**Decisions taken:**
- The project **will be released open source** — a `LICENSE` file is confirmed in scope.
- **`recommendation_extraction/` is out of scope** for this release. It exists to support the UI only.

---

## Scorecard vs. the 18 LiGHT checklist items

| # | Checklist item | Status | Evidence |
|---|---|---|---|
| 1 | Repo name & description clear | ⚠️ Partial | Name/acronym fine; GitHub description + topics unverified (no `gh` CLI available locally) |
| 2 | README strong opening summary | ❌ Fail | `README.md` §Summary, §Research Motivation, §Methods, §License are **empty headings**; stray `# Heading` at :92; TOC has placeholder "Main Section"/"Sub-Section" entries; typo "Motivatione" |
| 3 | Structure easy to navigate | ⚠️ Partial | Root `layout.json` (120 KB) unexplained; `playground.ipynb` is a 1-cell scratch notebook with saved outputs; `docs/instructions.md` committed but **empty** |
| 4 | Install instructions complete & tested | ❌ Fail | `requirements.txt` is a raw `pip freeze` with broken entries (see §7) |
| 5 | Quickstart works end-to-end | ❌ Fail | No runnable minimal example; every entry point needs manual input files |
| 6 | Main usage instructions clear | ⚠️ Partial | Technical-Report.md is thorough but its Folder Structure is **stale** (documents a `bucket/` dir that no longer exists) |
| 7 | Dependencies & external resources documented | ❌ Fail | OpenAI API key requirement only surfaces inside `scripts/screen_papers.sh`; no `.env.example`; no cost/hardware note |
| 8 | Data & model handling responsible | ❌ Fail | No provenance/licensing statement for scraped abstracts or downloaded PDFs |
| 9 | Reproducibility instructions | ❌ Fail | No seeds, no pinned model version policy, no expected-output description |
| 10 | Code quality sufficient for reuse | ❌ Fail | **Hardcoded personal cluster path** in both shell scripts (see §2) |
| 11 | Testing / validation provided | ❌ Fail | Zero tests in repo |
| 12 | License clear & appropriate | ✅ **Done** | Apache-2.0 `LICENSE` + `NOTICE` added; README §License filled. Data licensing still open — see §5 |
| 13 | Limitations & appropriate use stated | ❌ Fail | Nothing written; required emphasis for health/policy domains |
| 14 | Citation information | ❌ Fail | No `CITATION.cff`, no BibTeX |
| 15 | Maintainers & contact | ⚠️ Partial | 8 authors listed in README with no affiliation contact, no issue-reporting channel |
| 16 | Versioning & release history | ❌ Fail | No tags, no releases, no `CHANGELOG.md` |
| 17 | Repo hygiene before publication | ❌ Fail | Tracked `.pyc`; committed run artifacts; `.gitignore` gaps (see §1) |
| 18 | Maintenance status stated | ❌ Fail | Not declared anywhere |

**Score: 0 pass / 4 partial / 14 fail.** No secrets or credentials were found in tracked files or anywhere in git history — that is the one thing already clean.

---

## Phase 0 — Hygiene & safety (do first, ~1–2 h)

Checklist items 10, 17.

### 1. Purge tracked junk and close `.gitignore` gaps

- `git rm --cached __pycache__/arxiv_paper_search.cpython-310.pyc` — a compiled artifact is tracked.
- `.gitignore` currently misses `__pycache__/`, `*.pyc`, `.venv/`, `.env`, `*.egg-info`. Critically, `recommendation_extraction/.venv/` **exists on disk and is not ignored** — a single `git add -A` commits a full virtualenv (thousands of files, vendored third-party licences). Fix before any further commits.
- `.gitignore` line 8 ignores `.claude/` but `.claude/settings.local.json` predates it — confirm it is not tracked.

### 2. Remove hardcoded personal paths

Both cluster scripts hardcode another contributor's scratch directory:

- `scripts/screen_papers.sh:16` → `cd /mloscratch/users/arni/chitchat/CHITCHAT`
- `scripts/web_scrape.sh:15` → same

Replace with repo-root resolution:
```bash
cd "$(dirname "$0")/.." || exit 1
```
Checklist item 10 names "personal paths" explicitly as a failure mode.

### 3. Stop installing dependencies at runtime

`screen_papers.sh:63-68` and `web_scrape.sh:33-39` run `pip install --upgrade pip && pip install …` on every invocation. This contradicts `requirements.txt`, silently installs unpinned versions, and mutates the user's environment. Delete those blocks; document the env-setup step instead.

### 4. Decide the fate of committed artifacts

| Path | Size | Nature |
|---|---|---|
| `output/screening_results_20250811_100939.jsonl` | 1.7 MB | Timestamped run output |
| `output/screening_results_20250811_204753.jsonl` | — | Timestamped run output |
| `analyze_outputs/screening_results_2025081*.jsonl` (×3) | 44 KB | Timestamped run output |
| `data/screening_results_20250809_200422.jsonl` | — | Run output living in `data/` |
| `layout.json` | 120 KB | Unexplained root file |
| `playground.ipynb` | — | 1 cell, saved outputs |

**Recommendation:** keep one small, clearly-named sample (`data/sample_papers.json` + `data/sample_screening_results.jsonl`, ~20 records) to power the quickstart; move full run outputs to a tagged GitHub Release or Zenodo; delete or document `layout.json`; either promote `playground.ipynb` into a documented `notebooks/` example with outputs stripped, or delete it. Checklist item 17 names "unreviewed notebooks" explicitly.

---

## Phase 1 — Legal & governance (start now, longest lead time)

Checklist items 12, 14, 15, 18.

### 5. LICENSE — ✅ code licence done

Three separate licensing surfaces, per checklist item 12:

- **Code** (`src/`, `analysis/`, `scripts/`, `docs/diagrams/`) — ✅ **Apache-2.0 applied.** `LICENSE` holds the verbatim licence text (canonical form, so GitHub's licence detection recognises it); `NOTICE` carries the copyright line and institutional attribution, as referenced by Apache-2.0 §4(d); README §License now states it. Copyright is attributed to "The CHITCHAT Authors" (2025-2026) — a neutral form that avoids asserting institutional ownership. **If EPFL or KCL tech transfer requires copyright to vest in the institution by name, edit the `NOTICE` copyright line.**
- **Data** (`data/`, `output/`) — ⏳ pending. Code licences do not fit data. Recommend **CC-BY-4.0** in a separate `data/LICENSE`, but only for material CHITCHAT actually owns (see below).
- **Third-party content** — ⚠️ still needs a call. Screening outputs embed paper titles, abstracts and extracted full text scraped from Google Scholar, OpenAlex, Europe PMC and arXiv. CHITCHAT does not hold copyright in those abstracts and cannot relicense them, so CC-BY-4.0 cannot be applied wholesale. An interim disclaimer is now in `NOTICE` and in README §License. **Recommended resolution:** publish *derived* fields only — scores, classifications, DOIs/URLs, and the model's assessments — rather than redistributing abstracts and `extracted_text` verbatim. This shapes what §4 above keeps in the repo.

Although EPFL and KCL are both represented among the 8 contributors, the release decision is taken; flag the final licence choice to both institutions as a courtesy notification rather than treating it as a gate.

Confirmed clean: `research_paper_downloads/` (downloaded PDFs) is gitignored and never entered git history.

### 6. Governance files to add

- `CITATION.cff` — machine-readable; GitHub renders a "Cite this repository" button. Include all 8 authors with ORCIDs and affiliations.
- `CONTRIBUTING.md` — mirror the LiGHT docs workflow (branch → commit → PR to `main`), plus this repo's specifics: env setup, where API keys go, what not to commit.
- `CODE_OF_CONDUCT.md` — Contributor Covenant 2.1.
- `SECURITY.md` — where to report a leaked key or a data concern.
- `MAINTAINERS.md` or a README section — named maintainers with a real contact address; checklist item 15 wants a channel, not just a name list. The README's current 8-name list marks everyone "Main Contributor", which tells an outsider nothing about who to contact.
- **Maintenance status** (item 18) — pick one: actively maintained / experimental / archived. Given the v2 branch is mid-flight, "experimental, actively developed" is the honest label.

---

## Phase 2 — Reproducibility (~1 day)

Checklist items 4, 5, 7, 9.

### 7. Rebuild `requirements.txt` — it is currently broken

The file is a 93-line `pip freeze` dump of a whole environment, with concrete defects:

- **`pathlib==1.0.1`** — an abandoned PyPI backport that *shadows the stdlib `pathlib`* and is a well-known cause of install and build failures. Must be removed.
- **`fitz==0.0.1.dev2`** — the wrong package. `fitz` on PyPI is an unrelated stub; the code needs **PyMuPDF** (which the shell scripts do install, revealing the mismatch). PyMuPDF is absent from `requirements.txt`.
- **`bs4==0.0.2`** alongside `beautifulsoup4` — `bs4` is a dummy passthrough; drop it.
- **Missing packages actually imported**: `nltk`, `matplotlib`, `wordcloud` (used by `analysis/word_cloud_analysis.py`), plus PyMuPDF.
- **Unused weight**: `Sphinx` + 8 `sphinxcontrib-*` packages, `nipype`, `nibabel`, `pyxnat`, `prov`, `rdflib` — a neuroimaging stack with no corresponding code. These are `pip freeze` residue from an unrelated environment.

**Recommendation:** replace with a `pyproject.toml` declaring direct dependencies only, with a `requirements.txt` generated as the pinned lock. Then *actually test it* in a clean venv on both Linux and Windows — checklist item 4 says "complete and **tested**".

### 8. Remove the `recommendation_extraction/` orphan

`recommendation_extraction/` is **out of scope** for this release (UI-support only). Two tracked files need action:

- `recommendation_extraction/uv.lock` (809 KB) — tracked with **no `pyproject.toml`**, so it is unusable as committed (`uv sync` fails without the manifest). It is the second-largest file in the repo and pulls a competing dependency toolchain into an otherwise pip-based project. **Untrack it.**
- `recommendation_extraction/HUMANI-T_UI_SPEC.md` — keep if the UI spec is worth publishing alongside the pipeline; otherwise move it to the UI repo. Either way, exclude the directory from the release scope in the README and Technical Report.
- Add `recommendation_extraction/.venv/` to `.gitignore` regardless (see §1).

This leaves a single dependency system (pip + `pyproject.toml`) across the published repo.

### 9. Document external resources (item 7)

Add a README section covering: OpenAI API key (`OPENAI_API_KEY`) and rough cost per screening run; Python version (3.10, per the Technical Report); network access requirements; the fact that Google Scholar scraping via `scholarly` is rate-limited and may need a proxy. Ship a `.env.example`. Note that `screen_papers.py:193` pins `model="gpt-5-mini"` — state the model and date in the docs, since results are not reproducible across model versions.

### 10. Reproducibility statement (item 9)

Document exact commands for the full pipeline, expected outputs and record counts, and — honestly — that LLM screening and live web scraping are **not bit-reproducible**. Checklist item 9 explicitly allows "explain if full reproducibility impossible"; state the non-determinism rather than papering over it.

---

## Phase 3 — Documentation (~1–2 days)

Checklist items 2, 3, 6, 13.

### 11. Rewrite README

Current state: a template with the content never filled in. Sections needed, in checklist order —

- One-paragraph executive summary answering, on the first screen: what CHITCHAT is, why it exists, who it serves. Item 2 sets a **one-minute comprehension** bar.
- Expand the acronym meaningfully (currently just the letter-by-letter expansion).
- Fill §Summary, §Research Motivation, §Methods — all empty today.
- Remove the stray `# Heading` (:92) and the placeholder TOC rows ("Main Section" ×2, "Sub-Section" ×4); fix "Motivatione" (:20).
- Add: Quickstart, Installation, Pipeline overview, Limitations & Intended Use, License, Citation, Maintenance status.
- Fix the docs link at :9 — it points at `tree/main/docs`, but this work is on `v2`.

### 12. Limitations & appropriate use (item 13)

The checklist calls out health/law/policy domains specifically, and this project screens humanitarian-AI literature with an LLM assigning `humanity` / `impartiality` / `independence` / `neutrality` scores. Required statements: the LLM screening is a **decision aid, not a substitute for human systematic review**; scores are model judgments, not validated instruments; the corpus is English-language and skewed by source-repository coverage; screening results have not been validated against human annotators (or: report the agreement rate if you have it).

### 13. Fix the Technical Report

`docs/Technical-Report.md` (2,644 lines) is genuinely strong on module-level detail — keep it. But: its Folder Structure block (:274-320) documents a `bucket/` directory that does not exist and misplaces the `analysis/` contents; §Project Overview (:266) is empty; `TODO: Complete Table of Contents` sits at :10. Also fill or delete the empty `docs/instructions.md`.

---

## Phase 4 — Code quality & tests (~2 days)

Checklist items 10, 11.

### 14. Add a test suite

Zero tests exist today. Highest-value targets, all pure functions with no network dependency:

- `src/boolean/boolean_combinations.py` (75 lines) — deterministic string generation; trivially testable.
- `src/boolean/unique_boolean_combinations.py` (266 lines) — category combination logic, missing-key handling.
- `src/api/arxiv_paper_search.py::_extract_key_terms_from_boolean` — regex parsing of Boolean expressions.
- `src/screen_papers.py` — Pydantic schema validation against a recorded fixture response (mock the OpenAI call; never hit the API in CI).

Add `pytest` + a `tests/` dir + a GitHub Actions workflow running lint and tests on push. Checklist item 11 names pytest directly.

### 15. Code review pass

`analysis/*.py` totals ~2,000 lines across three scripts and has not been reviewed for reuse. Check for dead code, magic constants, and duplicated logic between `paper_analysis.py` and `web_scrape_analysis.py`. Add module-level docstrings stating input → output for each script.

---

## Phase 5 — Release (~half day)

Checklist items 1, 16, 18.

16. Set the GitHub **description** and **topics** (`llm`, `systematic-review`, `humanitarian-ai`, `literature-screening`, `epfl`) — item 1.
17. Add `CHANGELOG.md`; tag `v0.1.0`; cut a GitHub Release — item 16. There are currently no tags at all.
18. Enable Issues with bug/feature templates — supports item 15.
19. Merge `v2` → `main` (the README's docs link assumes `main`), and prune the stale `test-branch` / `unsupervised_clustering` branches or document why they exist.
20. Final sweep: re-run a secret scan, confirm no `.venv` or `__pycache__` entered history, verify a clean clone installs and runs the quickstart.

---

## Open question

**Dataset publication.** Do you intend to publish the screening corpus itself, or only the pipeline that produces it? This is the one item still unresolved, and it determines §4 (what stays in the repo) and §5 (whether the third-party abstract constraint needs a full data-licensing solution or just a "we ship derived fields only" note). Everything else can proceed without it.

## Suggested order

Phase 1 (licence text + governance files) starts **first** — it is cheap now that the release decision is taken, and item 12 gates publication. Phase 0 is quick and removes the embarrassing failures. Phases 2–3 are the bulk of the work. Phase 4 can proceed in parallel with 3. Phase 5 is the final gate.

Rough total: **4–6 working days** of hands-on work.

## Out of scope

- **`recommendation_extraction/`** — UI-support only; excluded from this release (see §8).
- **Hugging Face cards** — the LiGHT checklist also defines **Model Card** and **Dataset Card** standards. If the screening corpus is later published to HF, the Dataset Card checklist (11 items, 10 reader questions) applies on top of everything above, with provenance, consent and privacy sections that depend on the open question resolved first.
