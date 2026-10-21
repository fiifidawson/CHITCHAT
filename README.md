# CHITCHAT

*ArCHitectures for Interpretable & Transparent Continuous Humanitarian Alignment in chatbot Technologies*

CHITCHAT is a literature-review pipeline built on [mmore](https://github.com/EPFLiGHT/mmore). It finds papers, adds your own documents, removes personal data, screens papers with an LLM, and lets you ask questions with cited answers.

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
| 6 | `export` | Dataset, source tags and PRISMA report | `dataset.jsonl`, `dataset.csv`, `sources.json`, `prisma.md` |
| 7 | `index` | Chunks and indexes included papers and own documents | Milvus collection |
| – | `ask` | Answers a question with `[P0001]` citations | `answers.jsonl` |

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

A key already set in your shell or Windows environment wins over `.env`. `chitchat` warns you when the two differ.

### Milvus (for `index` and `ask`)

- **Linux and macOS:** nothing to install. Use a file, e.g. `db_uri: runs/{run_name}/milvus.db` (Milvus Lite).
- **Windows:** Milvus Lite has no Windows build. Run Milvus in Docker. Start Docker Desktop first, then in PowerShell:

```powershell
mkdir $HOME\milvus; cd $HOME\milvus      # outside the repo: Milvus keeps its data here
curl.exe -L https://github.com/milvus-io/milvus/releases/download/v2.6.25/milvus-standalone-docker-compose.yml -o docker-compose.yml
docker compose up -d
docker compose ps                         # wait until milvus-standalone is "healthy"
```

- Use `curl.exe`, not `curl`: in PowerShell, `curl` is `Invoke-WebRequest` and rejects `-L`.
- Use v2.6.24 or later. Older compose files use a MinIO image that is no longer on Docker Hub.
- Set `db_uri: http://127.0.0.1:19530` in your pipeline file. The smoke config already does.
- The `index` stage creates the database (`db_name`) if needed and rebuilds the collection on each run.
- Stop Milvus with `docker compose down`, run from that same folder.

The first `index` and `ask` download embedding models from Hugging Face (about 1 GB).

All commands on one page: [docs/COMMANDS.md](docs/COMMANDS.md). What each stage does, skips and reuses: [docs/PIPELINE.md](docs/PIPELINE.md). Use cases to try, with fictional sample documents: [docs/USE_CASES.md](docs/USE_CASES.md). Three end-to-end examples, step by step: [examples/README.md](examples/README.md).

## Start a search from your question

`chitchat search` turns your research question into a boolean search, lets you check and change it, then runs the pipeline in a new folder.

```powershell
uv run chitchat search "How do humanitarian organisations obtain informed consent when collecting data to train LLMs?"
uv run chitchat search --mode shallow "consent in LLM training data"
uv run chitchat search --predefined     # the fixed 8-category search in configs/discovery/
```

| | Shallow: quick scan | Deep: systematic search (default) |
|---|---|---|
| Clarifying questions | none | 4, before drafting |
| Search | 1 category, up to 4 concepts | 3 to 6 categories, 2 to 4 concepts each |
| Results | 10 per source | 25 per source, 2 pages |
| Full text | no: screens abstracts, so it takes minutes | yes: downloads PDFs |

1. In deep mode, answer a few questions first. Type a number to pick a suggestion, write your own answer, or press Enter to skip.
2. Check the draft: the concepts with their synonyms, and the boolean queries.
3. Type `a` to accept, `c` to ask for changes in plain words (for example "drop medical terms, add refugee camps"), or `q` to quit. You can ask for changes as many times as you like.
4. On accept, the search is saved in a new folder, e.g. `runs/humanitarian-organisations-obtain-informed-consent-2026-10-21/`, and the pipeline runs.
5. Later commands use that folder's config: `uv run chitchat ask -c runs/<folder>/pipeline.yaml "your question"`.

- Your question is checked for personal data on your machine before it goes to the LLM.
- Every query is kept under 1,500 characters, so OpenAlex can run it.
- Screening still uses `configs/criteria.example.yaml`, whatever the question.
- Options: `--yes` accepts the first draft without questions, `--plan-only` saves the search without running it, `--run-name` picks the folder name.

### Timing, history and logs

Each stage shows when it started and how long it took. A run ends with a Done (or Failed) box listing every stage's duration, the run id and the log file.

- `runs/<folder>/history.jsonl`: one line per run, with the run id, command, stages, durations and outcome.
- `runs/<folder>/logs/<run id>.log`: everything the run printed.
- `chitchat status` shows the last durations and the recent runs.

## Step by step: smoke test

The smoke config searches 2 categories with 3 results per source, so up to 18 papers. Outputs go to `runs/smoke/`. Run the steps one at a time and look at each output.

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

# 6. Dataset and PRISMA report. Open dataset.csv in Excel.
uv run chitchat run -c configs/pipeline.smoke.yaml --stages export
#    -> runs/smoke/dataset.csv, dataset.jsonl, sources.json, prisma.md

# 7. Index included papers in Milvus (start Milvus first, see Install)
uv run chitchat run -c configs/pipeline.smoke.yaml --stages index

# 8. Ask a question. Answers cite [P0001] tags and list their sources.
uv run chitchat ask -c configs/pipeline.smoke.yaml "What consent practices do the papers describe?"
uv run chitchat ask -c configs/pipeline.smoke.yaml --no-privacy "..."   # skip privacy mode
uv run chitchat ask -c configs/pipeline.smoke.yaml --review "..."       # check the context yourself first
#    -> answers are logged in runs/smoke/answers.jsonl

# Any time: what has each stage produced?
uv run chitchat status -c configs/pipeline.smoke.yaml
```

Privacy mode can mistake a product or project name for a person and mask it in your question. `ask` then shows the question it actually sent. Rephrase it ("the MoodSmith system") or use `--no-privacy`.

Or run them all at once:

```bash
uv run chitchat run -c configs/pipeline.smoke.yaml
```

Useful after screening:

```bash
# Rerun screen: finished papers are reused. Refused, invalid and failed ones are retried.
uv run chitchat run -c configs/pipeline.smoke.yaml --stages screen

# Changed only the `decision` rules? Recompute labels with no LLM calls, then rebuild the report.
uv run chitchat run -c configs/pipeline.smoke.yaml --redecide
uv run chitchat report -c configs/pipeline.smoke.yaml
```

Changing a question in the criteria file changes its hash, so the next `screen` asks the LLM again.

For about 20 or 30 papers, use `configs/pipeline.smoke20.yaml` or `configs/pipeline.smoke30.yaml` with the same commands. For about 55 papers with the full boolean search, use `configs/pipeline.smoke55.yaml`. Outputs go to `runs/smoke20/` or `runs/smoke30/`.

## Full run

```bash
cp configs/pipeline.example.yaml pipeline.yaml    # edit it if needed
uv run chitchat run                               # all stages, all 8 categories
uv run chitchat status
uv run chitchat ask "your question"
```

Papers that could not be downloaded are listed in `runs/<run>/raw/papers_failed_pdfs.csv`. Save a PDF at its `save_as` path and rerun `discover` to pick it up.

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

## Known limits

- **Screening criteria:** they are written for humanitarian AI data ethics. A search on another topic still uses them. Edit `configs/criteria.example.yaml` to change them.
- **PDFs:** publishers refuse many downloads, even with a subscription. Use the manual-download list from `discover`.
- **Masking:** it lowers risk but does not guarantee anonymity. Indirect identifiers can remain. The leakage check in `configs/rag_privacy.yaml` looks for this, but it is off by default because it costs extra LLM calls.
- **Screening:** it is an aid, not a final decision. Check the evidence quotes. Screenings from an abstract alone are weaker.
- **Costs:** screening makes one LLM call per paper, plus one more for extraction on papers that are not excluded. Each question costs one answer call. The leakage check adds 5 or more calls per question when on.
- **Windows:** Milvus needs Docker.

## Development

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

These tests need no network, models or API keys.

A tiny real run (arXiv, 3 papers) is marked `slow` and skipped by default. It uses your API key and Milvus when they are available:

```bash
uv run pytest -m slow
```

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
> The licence does not cover the papers and metadata the pipeline retrieves. They belong to their rights holders. If you share pipeline outputs, follow the terms of each source.
