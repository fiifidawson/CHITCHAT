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
| 1 | `discover` | Boolean search over OpenAlex, Europe PMC and arXiv, plus PDF download | `raw/papers.jsonl`, `raw/discovery_stats.json` |
| 2 | `ingest` | Reads your own documents | `raw/docs.jsonl` |
| 3 | `sanitize` | Masks personal data, with no LLM | `papers.sanitized.jsonl`, `docs.sanitized.jsonl` |
| 4 | `screen` | An LLM answers your criteria. Rules decide. | `screening.jsonl` |
| 5 | `export` | Dataset and PRISMA report | `dataset.jsonl`, `dataset.csv`, `prisma.md` |
| 6 | `index` | Chunks and indexes the included papers | Milvus collection |
| – | `ask` | Answers a question with `[P0001]` citations | `answers.jsonl` |

The search terms and screening criteria come from the earlier version of this project, kept in [legacy/](legacy/).

## Install

You need Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/fiifidawson/CHITCHAT.git
cd CHITCHAT
uv sync
uv run python -m spacy download en_core_web_lg
cp .env.example .env              # then add your API key
```

## Quick start

```bash
cp configs/pipeline.example.yaml pipeline.yaml
uv run chitchat run --stages discover
```

Papers that could not be downloaded are listed in `runs/<run>/raw/papers_failed_pdfs.csv`.
Save a PDF at its `save_as` path and rerun to pick it up.

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
