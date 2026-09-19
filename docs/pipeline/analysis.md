---
title: Stage 6 — Analysis
---

# Stage 6 — Analysis and visualisation

<span class="chit-status chit-status--planned">Placeholder</span>

!!! note "Work in progress"

    The analysis stage is the one part of the pipeline the original technical
    report never covered. The code exists and runs; this page is the
    placeholder for documenting it to the same standard as stages 1–5.

## What exists today

Three scripts under `legacy/analysis/`, each taking local files and producing
figures. None of them calls an external service, so this stage is fully
reproducible offline.

| Script | Input | Produces |
| --- | --- | --- |
| `word_cloud_analysis.py` | `papers.json` + `boolean_combinations.json` | Word clouds and frequency charts, one per topical bucket |
| `paper_analysis.py` | `screening_results_*.jsonl` | Priority distribution, publication timeline, technical-scope coverage, humanitarian-principle radar, methodology-vs-ethics scatter |
| `web_scrape_analysis.py` | `papers.json` | Source, venue and year breakdowns of the raw corpus, before screening |

## Where this is going

These three scripts are the basis of **LitLens**, the analytics layer being
extracted into a reusable package. The design is already written down in full:

[:octicons-arrow-right-24: LitLens design spec](../modules/litlens.md)

Rather than document the current scripts in detail and then document them
again after the extraction, this page will be written against the LitLens API
once it lands.

## Still needed

- [ ] Input and output format for each script
- [ ] The figures each one produces, with an example of each
- [ ] Configuration knobs — stopword lists, bucket definitions, output paths
- [ ] How to add a new plot
