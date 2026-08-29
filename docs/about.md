# About

**CHITCHAT** — *ArCHitectures for Interpretable & Transparent Continuous Humanitarian
Alignment in chatbot Technologies* — is a research project of the Laboratory of Intelligent
Global Health & Humanitarian Response Technologies at EPFL.

The repository holds the tooling behind the project's literature work: a reproducible
pipeline that turns a curated vocabulary of research concepts into Boolean search queries,
runs those queries across several academic repositories, collects and extracts the resulting
papers, and screens them for relevance.

## Why a pipeline

Systematic reviews at the intersection of AI and humanitarian practice are hard to keep
current. The relevant literature is spread across computer science preprints, open-access
indexes and life-sciences databases, and the search terms themselves are contested — what
counts as "humanitarian alignment" or "transparency" depends on which vocabulary you start
from.

Encoding the search as code rather than as a one-off manual query makes the process
repeatable and auditable: the term list, the Boolean logic derived from it, the repositories
queried, and the screening criteria are all version-controlled artefacts that can be
re-run and inspected.

## The pipeline

The stages run in sequence, each consuming the previous stage's output:

| Stage | What it does |
| --- | --- |
| **Boolean combinations** | Expands a structured word list — each term with its synonyms and near-synonyms — into quoted `OR` groups for exact-phrase matching. |
| **Unique combinations** | Joins those groups with `AND` across eight predefined research categories, from *Broad Foundational Search* through *Humanitarian & Social Impact* to *Environmental & Infrastructural Cost*. |
| **Multi-repository search** | Runs the resulting queries against arXiv, OpenAlex, Europe PMC and Google Scholar, respecting each API's rate limits and deduplicating across sources. |
| **Text extraction** | Downloads available PDFs, repairs and parses them, and extracts full text alongside the bibliographic metadata. |
| **Screening** | Applies LLM-assisted relevance assessment to the collected corpus, assigning priority classifications for human review. |
| **Analysis** | Produces summary plots over both the raw scrape and the screening results. |

Each stage reads and writes JSON, so any stage can be run, inspected or replaced on its own.

## Repository layout

The original pipeline lives under `legacy/`, which contains the source (`legacy/src/`),
the shell scripts that drive it (`legacy/scripts/`), the input vocabularies
(`legacy/data/`), the collected outputs (`legacy/output/`) and the analysis notebooks and
plotting code (`legacy/analysis/`).

The full stage-by-stage reference — function signatures, input and output schemas, error
handling and customisation points — is in
[`legacy/documentation/Technical-Report.md`](https://github.com/fiifidawson/CHITCHAT/blob/main/legacy/documentation/Technical-Report.md).

## Contributors

- **Annie Hartley** — EPFL
- **Laura Ferrarello** — EPFL
- **Johan Rochel** — EPFL
- **David Sasu** — EPFL
- **Tim Arni** — EPFL
- **Trevor Brokowski** — EPFL
- **Fiifi Dawson** — EPFL
- **Oriane Peter** — King's College London

## Licence

The source code is licensed under the **Apache License 2.0**; see
[`LICENSE`](https://github.com/fiifidawson/CHITCHAT/blob/main/LICENSE) and
[`NOTICE`](https://github.com/fiifidawson/CHITCHAT/blob/main/NOTICE).

That licence covers the code only. It does not extend to the third-party material the
pipeline retrieves — bibliographic metadata, abstracts and extracted document text from
arXiv, OpenAlex, Europe PMC and Google Scholar remain the property of their respective
rights holders and are not relicensed here. If you redistribute the pipeline's outputs, you
are responsible for complying with the terms of the originating repository and of the
underlying publications.
