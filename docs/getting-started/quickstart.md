---
title: Quickstart
---

# Quickstart

<span class="chit-status chit-status--planned">Placeholder</span>

!!! note "Work in progress"

    A minimal, runnable end-to-end example does not exist yet. Every entry
    point currently needs input files that a newcomer has no way to produce,
    which the project's [readiness audit](../project/roadmap.md) records as an
    open gap. This page is the placeholder for that example.

## What the quickstart should do

Run the whole pipeline on a deliberately tiny vocabulary, in under five
minutes, on one machine, producing a handful of screened papers and one plot.

## Intended shape

```bash
# 1. Build Boolean OR-groups from a small sample vocabulary
python legacy/src/boolean/boolean_combinations.py

# 2. Compose them into per-category queries
python legacy/src/boolean/unique_boolean_combinations.py

# 3. Search one repository (arXiv needs no key)
python legacy/src/api/arxiv_paper_search.py

# 4. Screen the results
export OPENAI_API_KEY="..."
python legacy/src/screen_papers.py \
    legacy/documentation/prompt/paper_screening_prompt.txt \
    legacy/data/test_papers.json

# 5. Plot what came back
python legacy/analysis/paper_analysis.py
```

## Still needed

- [ ] A trimmed sample vocabulary that returns results in seconds, not hours
- [ ] A committed `data/sample_papers.json` fixture so stages 4–6 can run alone
- [ ] Expected output — record counts and a reference figure — so a reader can
      tell whether their run worked
- [ ] Wall-clock timing and an estimate of the OpenAI cost per run

## Meanwhile

Follow [Installation](installation.md), then work through the
[pipeline reference](../pipeline/index.md) stage by stage. Each stage page
documents its own input and output format, so you can enter the pipeline
wherever you already have the data.
