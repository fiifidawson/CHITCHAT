# CHITCHAT — codebase guide

An orientation map for anyone working on this repository: what each part does,
how data moves between the parts, and **which file to open** for a given change.

This is a working document for maintainers. The published documentation lives in
`docs/` and is a different thing — it explains the pipeline to users, not the
repository to contributors.

> **Naming.** *CHITCHAT* is the research project and the pipeline. *Humani-T* is
> the application built on top of the corpus the pipeline produces. Keep them
> distinct in code, commits and copy.

---

## 1. The shape of the repository

```
CHITCHAT/
├── main.py                    # 6-line stub; not wired to anything yet
├── mkdocs.yml                 # documentation site config
├── overrides/home.html        # landing-page hero template
├── docs/                      # documentation site source
├── legacy/                    # the pipeline — all working code lives here
├── requirements.txt           # pipeline deps (curated direct deps)
├── pyproject.toml             # documentation deps (working) + uv config
├── uv.lock                    # resolved docs toolchain, committed
├── LICENSE / NOTICE           # Apache-2.0 + third-party content clause
└── .github/workflows/docs.yml # builds and deploys the docs site
```

Two things surprise people:

1. **All the real code is under `legacy/`.** The name is aspirational, not
   pejorative — it marks code that works and produced the current review, but
   that is being extracted into reusable packages. Nothing is installable; there
   is no `pyproject.toml` and no importable `chitchat` module.
2. **`main.py` is a stub.** It prints `"Hello from chitchat!"` and is not an
   entry point to anything. If you are looking for where the pipeline starts,
   it is not here — see §2.

---

## 2. The pipeline

The architecture is a chain of files. Each stage reads one JSON file and writes
another, which is what makes any stage re-runnable, inspectable and replaceable
on its own.

```
structure.json                  (authored by hand — the vocabulary)
   │  legacy/src/boolean/boolean_combinations.py
   ▼
boolean_combinations.json       (one quoted OR-group per concept)
   │  legacy/src/boolean/unique_boolean_combinations.py
   ▼
unique_boolean_combinations.json  (AND-composed, one query per category)
   │  legacy/src/api/arxiv_paper_search.py  +  legacy/src/api/web_scrape.py
   ▼
obtained_lit.json               (Paper records: metadata, abstract, full text)
   │  legacy/src/screen_papers.py            ← needs OPENAI_API_KEY
   ▼
screening_results_<ts>.jsonl    (one structured screening record per paper)
   │  legacy/analysis/*.py
   ▼
plots / dashboards
```

### Stage-by-stage file map

| Stage | File | Lines | Entry point |
|---|---|---|---|
| 0 · vocabulary conversion | `legacy/src/boolean/csv_to_json.py` | 23 | module-level script — no entry function |
| 1 · Boolean OR-groups | `legacy/src/boolean/boolean_combinations.py` | 75 | `generate_boolean_combinations()` |
| 2 · category queries | `legacy/src/boolean/unique_boolean_combinations.py` | 266 | `UniqueBooleanCombinationsGenerator`, `generate_unique_boolean_combinations()` |
| 3 · arXiv | `legacy/src/api/arxiv_paper_search.py` | 370 | `ArxivPaperSearcher`, `search_arxiv_papers()` |
| 4 · other repositories | `legacy/src/api/web_scrape.py` | 555 | `get_llit_papers()` (orchestrator), `search_repository()` (dispatcher) |
| 5 · screening | `legacy/src/screen_papers.py` | 353 | `main()`, `screen_paper()` |
| 6 · analysis | `legacy/analysis/*.py` | ~2,060 | `main()` in each |

### Stage 4 in more detail

`web_scrape.py` is the messiest file and the one most likely to break, because
it wraps three very different sources:

| Function | Source | Notes |
|---|---|---|
| `search_openalex()` | OpenAlex | Abstracts arrive as an inverted index; `_rebuild_abstract()` reassembles them |
| `search_europepmc()` | Europe PMC | Straightforward REST |
| `search_google_scholar_scholarly()` | Google Scholar | **Scraped, not an API.** The fragile one — blocks aggressively |
| `get_arxiv_results()` | arXiv | Reads what stage 3 already wrote |
| `search_repository()` | — | Dispatcher: maps a source name to the functions above |
| `get_llit_papers()` | — | Orchestrator: runs everything, deduplicates, downloads PDFs |
| `download_research_paper()` / `extract_paper_text()` | — | PDF fetch and text extraction |

### Stage 5 in more detail

`screen_papers.py` has the cleanest design in the repository: a Pydantic model
tree that the LLM response is validated against, rather than prose parsed with
regexes.

```
PaperScreening
├── PublicationQuality
├── TechnicalScope
├── HumanitarianPrinciples   ← humanity / impartiality / independence / neutrality, each 0–3
├── EthicalFlags
├── MethodologyContributions
├── EthicalContributions
└── PriorityLevel            ← HIGH / MEDIUM / LOW PRIORITY, EXCLUDE
```

Results are appended to JSONL as they are produced, and `load_processed_ids()`
skips papers already done — so an interrupted run resumes rather than restarting.

---

## 3. Where to make changes

This is the part to bookmark.

### Change the search vocabulary

**`legacy/data/structure.json`** — a JSON **list** of 23 objects, each shaped:

```json
{
  "WORD": "Foundation model",
  "SYNONYMS AND NEAR SYNONYMS": "Base model, Pre-trained model, General-purpose model, ..."
}
```

Synonyms are a single comma-separated string, not a list. `boolean.csv` in the
same directory is the human-authored source.

`csv_to_json.py` converts the CSV, but mind three things: it runs at import time
with no `main()` guard, it reads the hardcoded relative path
`'../../data/boolean.csv'` (so it only works when run from inside
`legacy/src/boolean/`), and **it writes `output.json`, not `structure.json`** —
you have to move the result into place yourself.

After editing, re-run stages 1 and 2 to regenerate the queries.

### Change which categories are searched

**`legacy/src/boolean/unique_boolean_combinations.py:17`** — the
`self.predefined_combinations` dict. Eight categories today:

| Category | Concept keys |
|---|---|
| Broad Foundational Search | 8 |
| Humanitarian & Social Impact Search | 11 |
| Inclusion & Representation Search | 8 |
| Transparency & Accountability Search | 7 |
| Harm Reduction & Safety Search | 5 |
| Control, Consent & Personal Data Rights | 5 |
| Consent, Agency & Participatory AI | 4 |
| Environmental & Infrastructural Cost | 7 |

Add a category by adding a key whose value is a list of `WORD` values from
`structure.json`. `update_predefined_combination(category, new_keys)` does the
same at runtime without editing the file.

> This is a **research** change, not a code change. Altering the categories
> changes what the review finds. Treat it as an experimental decision and
> record it.

### Add a new paper source

Three edits, in `legacy/src/api/web_scrape.py`:

1. Write `search_<source>(query, max_results, ...)` returning the same `Paper`
   dict shape the existing searchers return.
2. Register it in `search_repository()` (the dispatcher).
3. Add it to the source list `get_llit_papers()` iterates over.

Check how the source handles Boolean syntax first — each one differs, and
`arxiv_paper_search.py::_extract_key_terms_from_boolean` exists precisely
because arXiv will not take the full expression.

### Change the screening schema or prompt

| To change | Edit |
|---|---|
| What is scored | The Pydantic models at `legacy/src/screen_papers.py:16–83` |
| How it is asked | `legacy/documentation/prompt/paper_screening_prompt.txt` |
| Which model | `legacy/src/screen_papers.py:193` — currently hardcoded `model="gpt-5-mini"` |

> Changing any of these changes the scores. The model identifier is part of the
> experimental record, not an implementation detail. Old result files were
> produced under the old schema and will not have the new fields — there is no
> schema version marker yet, which is a known gap.

### Add or change a plot

| Want | File |
|---|---|
| Screening dashboards (priority, timeline, humanitarian radar) | `legacy/analysis/paper_analysis.py` — nine `plot_*` functions |
| Raw-corpus analytics (year, source, venue) | `legacy/analysis/web_scrape_analysis.py` — `PaperAnalyzer` methods |
| Word clouds per topical bucket | `legacy/analysis/word_cloud_analysis.py` — five classes |

`paper_analysis.py` and `web_scrape_analysis.py` have overlapping logic that has
never been reconciled; check both before adding a helper.

---

## 4. The documentation site

Built with MkDocs + Material for MkDocs. Pinned to `mkdocs>=1.6,<2` deliberately
— MkDocs 2.0 removes the plugin system and Material does not follow it.

The docs toolchain is declared in the `docs` dependency group in
`pyproject.toml` — there is no `requirements-docs.txt`.

```bash
uv sync                      # installs the `docs` group (a default group)
mkdocs serve                 # then open http://127.0.0.1:8000/CHITCHAT/
mkdocs build --strict        # what CI runs (CI uses `uv sync --locked`)
```

Without `uv`, use `pip install --group docs` instead (needs pip >= 25.1).

> **The `/CHITCHAT/` path matters.** `site_url` ends in `/CHITCHAT/` so the
> local server mirrors GitHub Pages. The bare root 302-redirects and looks
> broken if you do not know this.
>
> If port 8000 is busy — Docker Desktop and VS Code both like it — use
> `mkdocs serve -a 127.0.0.1:8080`.

### Where to make documentation changes

| To change | Edit |
|---|---|
| Any page's text | The matching file under `docs/` |
| Navigation, tabs, page order | The `nav:` block in `mkdocs.yml` — **a new page must be added here or it will not appear** |
| Colours, fonts, spacing, cards | `docs/stylesheets/extra.css` |
| The landing-page hero and its artwork | `overrides/home.html` (inline SVG lives here) |
| Landing-page body below the hero | `docs/index.md` |
| Markdown features, plugins | `markdown_extensions:` / `plugins:` in `mkdocs.yml` |
| Deploy behaviour | `.github/workflows/docs.yml` |

### Two traps in the site theme

**1. The hero inherits the wrong font scale.** Material sets
`body { font-size: .5rem }` (10px) and `.md-typeset { font-size: .8rem }`
(16px). The hero in `overrides/home.html` sits *outside* `.md-typeset`, so
anything you add there renders at 10px unless you set a size explicitly. This
already bit the hero buttons once.

**2. Brand blue fails contrast on white.** `#54A4E4` measures **2.7:1** against
white and fails WCAG AA. It is decorative only — rules, tints, hover borders.
Text and links use `#1668B0` on light (5.8:1) and `#7FBDF0` on dark (6.1:1).
The palette is defined once at the top of `extra.css`; change it there, not at
the call sites.

### Adding a page

1. Create the `.md` file under the right section directory.
2. Add it to `nav:` in `mkdocs.yml`.
3. Run `mkdocs build --strict` — it fails on broken internal links and on pages
   that exist but are not in `nav`.

If you move or delete a page that already has a public URL, add an entry to the
`redirects.redirect_maps` block in `mkdocs.yml`.

---

## 5. Running the pipeline

There is no single entry point and **no working quickstart** — every stage needs
input files a newcomer has no way to produce. This is the largest gap in the
project.

```bash
python3.10 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt  # see §7 — this does not currently work

export OPENAI_API_KEY="sk-..."   # stage 5 only; nothing else authenticates
python legacy/src/screen_papers.py <prompt.txt> <papers.json>
```

`legacy/scripts/web_scrape.sh` and `screen_papers.sh` are the cluster entry
points for EPFL RCP. **Do not run them as-is** — see §7.

---

## 6. Data files

| Path | What it is | Safe to edit? |
|---|---|---|
| `legacy/data/boolean.csv` | Vocabulary, as authored | Yes — the human source of truth |
| `legacy/data/structure.json` | Vocabulary, as the pipeline reads it | Yes — but edit `boolean.csv` too, or the two drift |
| `legacy/data/boolean_combinations.json` | Stage 1 output | No — generated |
| `legacy/data/test_papers.json` | Small fixture | Yes |
| `legacy/data/screening_results_20250809_200422.jsonl` | A run artefact living in `data/` | Misfiled; belongs in `output/` |
| `legacy/output/`, `legacy/analyze_outputs/` | Timestamped run artefacts, up to 1.7 MB | No — outputs, not fixtures |

---

## 7. Known problems

Do not spend an afternoon rediscovering these. The full audit is in
`legacy/documentation/OSS-Readiness-Plan.md`.

| Problem | Where | Detail |
|---|---|---|
| **Hardcoded personal cluster path** | `legacy/scripts/screen_papers.sh:16`, `web_scrape.sh:15` | Both `cd /mloscratch/users/arni/chitchat/CHITCHAT`. Replace with `cd "$(dirname "$0")/.."` |
| **Scripts pip-install at runtime** | `screen_papers.sh:63`, `web_scrape.sh:33` | Mutates the caller's environment on every invocation and contradicts `requirements.txt` |
| **Relative default paths** | `boolean_combinations.py:3` | Defaults are `'../../data/structure.json'` — correct only when run from inside `legacy/src/boolean/` |
| **Zero tests** | everywhere | The pure functions in `legacy/src/boolean/` are the obvious first targets |
| **No schema version on results** | `screen_papers.py` | Old JSONL files cannot be distinguished from new ones |

---

## 8. Planned direction

Two packages are specified but **not implemented**. The specs are detailed
enough to build from:

| Package | Extracted from | Spec |
|---|---|---|
| `paper_discovery` | `legacy/src/boolean/`, `legacy/src/api/` | `docs/modules/paper-discovery.md` |
| `litlens` | `legacy/analysis/` | `docs/modules/litlens.md` |

If you are about to refactor either area, read the spec first — it may already
describe the interface you are about to invent.

Humani-T (the application) is at Version 1, in development, in two deployments:
web-served and local-served. Its documentation placeholders are in
`docs/humani-t/`. `legacy/recommendation_extraction/` holds a UI spec supporting
it and is excluded from the pipeline's open-source release.

---

## 9. Before you commit

- `mkdocs build --strict` if you touched anything under `docs/`, `mkdocs.yml`
  or `overrides/`.
- Do not commit API keys. `.gitignore` covers `.env`, `.venv`, `__pycache__/`
  and `/site`.
- Do not commit run outputs. If a stage wrote a timestamped file, it belongs in
  a release or an archive, not in git.
- If you changed the vocabulary, the categories, the prompt or the model, say so
  in the commit message — those change what the review finds, and that is the
  part future readers will need to reconstruct.
