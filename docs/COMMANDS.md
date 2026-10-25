# Commands

Every command runs from the repo root, on Windows (PowerShell) and macOS (Terminal) alike. Where they differ, both are shown.

`-c <config>` picks the run. Without it, `pipeline.yaml` in the repo root is used. After `chitchat search`, use the config it wrote: `-c runs/<folder>/pipeline.yaml`.

Related pages: [SETUP.md](SETUP.md) to install, [PIPELINE.md](PIPELINE.md) for what each stage does, [../examples/README.md](../examples/README.md) for worked examples.

## Plan a search from your question

| Command | What it does |
|---|---|
| `uv run chitchat search "question"` | Deep search: clarifying questions, 3 to 6 categories, then you confirm and it runs |
| `uv run chitchat search --mode shallow "question"` | Quick scan: no questions, 1 to 3 categories, abstracts only |
| `uv run chitchat search --plan-only "question"` | Plans and saves the search, but doesn't run it |
| `uv run chitchat search --yes "question"` | No questions: accepts the first draft and runs |
| `uv run chitchat search --run-name my-review "question"` | Names the run folder yourself |
| `uv run chitchat search --predefined` | The fixed 8-category search in `configs/discovery/`, in a new run folder |
| `uv run chitchat search -c examples/thorough/pipeline.yaml "question"` | Uses another template for the settings |

While planning:

- **Clarifying questions** (deep mode): type a number to pick a suggestion, your own answer, or press Enter to skip.
- **The draft** shows one box per category: its concepts joined by `AND`, each with its synonyms after `or:`, and the query's length with the OpenAlex status on the bottom border.
- **Your choice:** `a` accepts, `c` asks for changes in plain words, `q` quits and saves nothing.

Searches go to OpenAlex, Europe PMC and arXiv. To change that, see [Choosing sources](PIPELINE.md#choosing-sources).

## Run stages

| Command | What it does |
|---|---|
| `uv run chitchat run -c <config>` | Runs every stage in order |
| `uv run chitchat run -c <config> --stages screen,export` | Runs only the stages you list, in pipeline order |
| `uv run chitchat run -c <config> --redecide` | Relabels screened papers with the current rules. No LLM calls |
| `uv run chitchat report -c <config>` | Rebuilds `dataset.csv`, `dataset.jsonl` and the PRISMA report |

| Stage | What it does |
|---|---|
| `queries` | Shows the boolean queries: categories, their concepts, length, OpenAlex status. Offline |
| `discover` | Searches OpenAlex, Europe PMC and arXiv, and downloads PDFs |
| `ingest` | Reads your own documents from the configured folder. Skipped if there is none |
| `sanitize` | Masks personal data. No LLM, nothing leaves your machine |
| `screen` | The LLM answers the criteria, fixed rules decide the label. Finished papers are reused |
| `export` | Writes `dataset.csv`, `dataset.jsonl`, `sources.json` and the PRISMA report |
| `index` | Puts the included papers and your documents into the search index |

## Ask and check

| Command | What it does |
|---|---|
| `uv run chitchat ask -c <config> "question"` | Answers from the index, citing `[P0001]` (papers) and `[D0001]` (your documents) |
| `uv run chitchat ask -c <config> --no-privacy "question"` | Same, without the privacy check on the question |
| `uv run chitchat ask -c <config> --review "question"` | Shows you the masked context and waits for your approval before sending |
| `uv run chitchat ask -c <config> --k 15 "question"` | Uses 15 passages instead of the default 6 |
| `uv run chitchat status -c <config>` | Which stages are done, how long they took, what they produced, and the last runs |

## Test configs

These run in place, without a search. Outputs go to `runs/<name>/`.

| Config | Papers | Use it to |
|---|---|---|
| `configs/pipeline.smoke.yaml` | up to 18 (2 categories) | Check the setup end to end, quickly |
| `configs/pipeline.smoke20.yaml` | about 20 | A slightly bigger quick run |
| `configs/pipeline.smoke30.yaml` | about 30 | A small test with more variety |
| `configs/pipeline.smoke55.yaml` | about 55 (all 8 predefined categories, Europe PMC and arXiv) | Test the full predefined search |

## Stage by stage: the smoke test

Run the stages one at a time and look at each output. Up to 18 papers, outputs in `runs/smoke/`.

```bash
# 1. Boolean queries (offline). Check the categories and their concepts.
uv run chitchat run -c configs/pipeline.smoke.yaml --stages queries

# 2. Search the sources and download PDFs (a few minutes).
uv run chitchat run -c configs/pipeline.smoke.yaml --stages discover

# 3. Your own documents (optional). Put files in my_docs/ first.
uv run chitchat run -c configs/pipeline.smoke.yaml --stages ingest

# 4. Mask personal data. No LLM.
uv run chitchat run -c configs/pipeline.smoke.yaml --stages sanitize

# 5. Screen with the LLM. Only masked text is sent.
uv run chitchat run -c configs/pipeline.smoke.yaml --stages screen

# 6. Dataset and PRISMA report. Open runs/smoke/dataset.csv in Excel.
uv run chitchat run -c configs/pipeline.smoke.yaml --stages export

# 7. Build the search index (Windows: Milvus must be running).
uv run chitchat run -c configs/pipeline.smoke.yaml --stages index

# 8. Ask, and check progress.
uv run chitchat ask -c configs/pipeline.smoke.yaml "What consent practices do the papers describe?"
uv run chitchat status -c configs/pipeline.smoke.yaml
```

## Your own documents

Put them in `my_docs/` in the repo root (it is ignored by git, so they stay private). To try the fictional samples:

| Windows (PowerShell) | macOS (Terminal) |
|---|---|
| `New-Item -ItemType Directory -Force my_docs; Copy-Item examples/my_docs/* my_docs/` | `mkdir -p my_docs && cp examples/my_docs/* my_docs/` |

## Milvus (the search index)

`index.db_uri: auto` in the configs means Milvus in Docker on Windows, and a `milvus.db` file in the run folder on macOS and Linux.

| Windows (PowerShell) | What it does |
|---|---|
| `docker start milvus-etcd milvus-minio milvus-standalone` | Starts Milvus (after a restart, if it isn't set to start by itself) |
| `docker ps --filter "name=milvus"` | Shows whether it is running and `healthy` |
| `docker stop milvus-standalone milvus-minio milvus-etcd` | Stops it |

Full Milvus setup: [SETUP.md](SETUP.md), Windows step 7.

## Timing, history and logs

Every `run`, `report` and `search` prints each stage's start time and duration, and ends with a Done, Failed or Interrupted box. It is recorded in `runs/<folder>/history.jsonl`, and its output is saved in `runs/<folder>/logs/<run id>.log`.

## Development

| Command | What it does |
|---|---|
| `uv run pytest` | Fast tests. No network, models or API keys |
| `uv run pytest -m slow` | A tiny real run, end to end (uses your API key and Milvus) |
| `uv run ruff check .` | Lint |
| `uv run ruff format .` | Format |
| `uv run python examples/make_samples.py` | Rebuilds the Word, PDF and Excel sample documents |
