# CHITCHAT

*ArCHitectures for Interpretable & Transparent Continuous Humanitarian Alignment in chatbot Technologies*

CHITCHAT is a literature-review pipeline built on [mmore](https://github.com/EPFLiGHT/mmore).
It finds papers, adds your own documents, removes personal data, screens papers with an LLM,
and lets you ask questions with cited answers.

It is a research project of the LiGHT lab at EPFL, with the ICRC.

> [!IMPORTANT]
> Screening is an aid, not a final decision. Every answer comes with an evidence quote so a person can check it.

## The pipeline

| # | Stage | What it does | Output in `runs/<run>/` |
|---|---|---|---|
| 1 | `queries` | Builds the boolean search from the synonyms and categories. Offline. | `queries.json` |
| 2 | `discover` | Searches OpenAlex, Europe PMC and arXiv, and downloads PDFs | `raw/papers.jsonl`, `raw/discovery_stats.json` |
| 3 | `ingest` | Reads your own documents from `my_docs/` | `raw/docs.jsonl` |
| 4 | `sanitize` | Masks personal data. No LLM. | `papers.sanitized.jsonl`, `docs.sanitized.jsonl`, `privacy_report.json` |
| 5 | `screen` | An LLM answers your criteria. Rules decide the label. | `screening.jsonl` |
| 6 | `export` | Dataset and PRISMA report (coming next) | `dataset.jsonl`, `dataset.csv`, `prisma.md` |
| 7 | `index` | Indexes the included papers (coming next) | Milvus collection |
| – | `ask` | Answers a question with `[P0001]` citations (coming next) | `answers.jsonl` |

The search terms and screening criteria come from the earlier version of this project, kept in [legacy/](legacy/).

## Install

You need Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/fiifidawson/CHITCHAT.git
cd CHITCHAT
uv sync                                           # slow network? UV_HTTP_TIMEOUT=300 uv sync
uv run python -m spacy download en_core_web_lg    # needed by the sanitize stage
cp .env.example .env                              # then add OPENAI_API_KEY
```

## Step by step: smoke test

The smoke config searches 2 categories with 3 results per source, so up to 18 papers.
Outputs go to `runs/smoke/`. Run the steps one at a time and look at each output.

```bash
# 1. Boolean queries (offline). Check the AND/OR groups.
uv run chitchat run -c configs/pipeline.smoke.yaml --stages queries
#    -> runs/smoke/queries.json

# 2. Search the sources and download PDFs. Takes a few minutes.
uv run chitchat run -c configs/pipeline.smoke.yaml --stages discover
#    -> runs/smoke/raw/papers.jsonl, raw/discovery_stats.json, raw/papers_failed_pdfs.csv

# 3. Optional: your own documents. Put files in my_docs/ first.
uv run chitchat run -c configs/pipeline.smoke.yaml --stages ingest
#    -> runs/smoke/raw/docs.jsonl

# 4. Privacy: mask names, emails and phone numbers. No LLM, nothing leaves your machine.
uv run chitchat run -c configs/pipeline.smoke.yaml --stages sanitize
#    -> runs/smoke/papers.sanitized.jsonl, privacy_report.json

# 5. AI screening. Needs OPENAI_API_KEY. Only sanitized text is sent.
uv run chitchat run -c configs/pipeline.smoke.yaml --stages screen
#    -> runs/smoke/screening.jsonl
```

Or run them all at once:

```bash
uv run chitchat run -c configs/pipeline.smoke.yaml
```

Useful after screening:

```bash
# Rerun screen: finished papers are reused. Refused, invalid and failed ones are retried.
uv run chitchat run -c configs/pipeline.smoke.yaml --stages screen

# Changed only the `decision` rules? Recompute labels with no LLM calls.
uv run chitchat run -c configs/pipeline.smoke.yaml --redecide
```

Changing a question in the criteria file changes its hash, so the next `screen` asks the LLM again.

## Full run

```bash
cp configs/pipeline.example.yaml pipeline.yaml    # edit it if needed
uv run chitchat run                               # all stages, all 8 categories
```

Papers that could not be downloaded are listed in `runs/<run>/raw/papers_failed_pdfs.csv`.
Save a PDF at its `save_as` path and rerun `discover` to pick it up.

## Configuration

| File | What it sets |
|---|---|
| `pipeline.yaml` | One run: which configs to use, the screening model, the index |
| `configs/discovery/synonyms.jsonl` | Search words and their synonyms |
| `configs/discovery/categories.yaml` | Which words are combined in each search |
| `configs/discovery/discovery.yaml` | Sources, result limits, PDF download |
| `configs/criteria.example.yaml` | Screening questions and decision rules |
| `configs/sanitize.yaml` | Which personal data is masked |
| `configs/rag_privacy.yaml` | Privacy checks when answering questions |

## Privacy

- Raw text stays in `runs/<run>/raw/`. Do not share that folder.
- Everything else holds sanitized text only.
- Papers and own documents use different entity lists. Papers keep places and dates, which are research content.
- Authors cited in a paper's references are masked too. This is expected.
- Masking lowers risk but does not guarantee anonymity.

## Development

```bash
uv run ruff check .
uv run pytest
```

Tests need no network, models or API keys.

## Main authors

- **Annie Hartley**, EPFL
- **Laura Ferrarello**, EPFL
- **Johan Rochel**, EPFL
- **David Sasu**, EPFL
- **Tim Arni**, EPFL
- **Trevor Brokowski**, EPFL
- **Fiifi Dawson**, EPFL
- **Oriane Peter**, King's College London

## License

The code is under the Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

> [!CAUTION]
> The licence does not cover the papers and metadata the pipeline retrieves.
> They belong to their rights holders. If you share pipeline outputs, follow the terms of each source.
