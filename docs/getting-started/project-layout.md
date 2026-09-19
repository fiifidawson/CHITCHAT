---
title: Project layout
---

# Project layout

The pipeline as it was originally written lives under `legacy/`. That name is
deliberate: the code works and is what produced the current review, but it is
being extracted into reusable packages — see [Modules](../modules/index.md) —
and the layout will change when that lands.

```text
CHITCHAT/
├── docs/                          # this documentation site
├── mkdocs.yml                     # site configuration
├── requirements.txt               # pipeline dependencies (direct deps only)
├── pyproject.toml                 # documentation dependencies (`docs` group)
├── uv.lock                        # resolved docs toolchain, committed
├── LICENSE                        # Apache-2.0
├── NOTICE                         # copyright + third-party content clause
└── legacy/
    ├── src/
    │   ├── boolean/
    │   │   ├── csv_to_json.py                   # boolean.csv → structure.json
    │   │   ├── boolean_combinations.py          # stage 1: OR-groups
    │   │   └── unique_boolean_combinations.py   # stage 2: AND-composed queries
    │   ├── api/
    │   │   ├── arxiv_paper_search.py            # stage 3: arXiv
    │   │   └── web_scrape.py                    # stage 4: OpenAlex, Europe PMC, Scholar
    │   └── screen_papers.py                     # stage 5: LLM screening
    ├── analysis/
    │   ├── paper_analysis.py                    # screening dashboards
    │   ├── web_scrape_analysis.py               # raw-corpus analytics
    │   └── word_cloud_analysis.py               # per-bucket word clouds
    ├── scripts/
    │   ├── web_scrape.sh                        # cluster entry point
    │   └── screen_papers.sh                     # cluster entry point
    ├── data/
    │   ├── boolean.csv                          # the curated vocabulary, as authored
    │   ├── structure.json                       # the vocabulary, as the pipeline reads it
    │   ├── boolean_combinations.json            # stage 1 output
    │   └── test_papers.json                     # small fixture
    ├── documentation/
    │   ├── diagrams/                            # Excalidraw sources + generator
    │   └── prompt/paper_screening_prompt.txt    # the screening prompt
    ├── assets/                                  # logo, doc icon
    ├── output/                                  # run artefacts (timestamped)
    └── analyze_outputs/                         # analysis artefacts
```

## How to read it

The pipeline is a chain of files, not a framework. Each stage reads one JSON
file and writes another:

| You have | Run | You get |
| --- | --- | --- |
| `data/structure.json` | `src/boolean/boolean_combinations.py` | `boolean_combinations.json` |
| `boolean_combinations.json` | `src/boolean/unique_boolean_combinations.py` | `unique_boolean_combinations.json` |
| `unique_boolean_combinations.json` | `src/api/arxiv_paper_search.py`, `src/api/web_scrape.py` | `obtained_lit.json` |
| `obtained_lit.json` + a prompt | `src/screen_papers.py` | `screening_results_*.jsonl` |
| `screening_results_*.jsonl` | `analysis/paper_analysis.py` | plots |

That is the whole architecture. It means any stage can be re-run, inspected or
replaced on its own, and that you can enter the pipeline wherever you already
have the input.

## Things to know

!!! warning "Committed run artefacts"

    `legacy/output/` and `legacy/analyze_outputs/` contain timestamped results
    from past runs, some of them multi-megabyte. They are kept for now as a
    record, but they are outputs, not inputs — do not treat them as fixtures.
    Moving them out of the repository is tracked on the
    [Roadmap](../project/roadmap.md).

!!! note "Out of scope"

    `legacy/recommendation_extraction/` supports the [Humani-T](../humani-t/index.md)
    interface and is excluded from the open-source release of the pipeline.
