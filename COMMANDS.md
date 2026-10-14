# Commands

Every command runs from the repo root. Add `-c <config>` to pick a run; the default is `pipeline.yaml`.

## Configs

| Config | What it is |
|---|---|
| `configs/pipeline.smoke.yaml` | Quick test: 2 categories, up to 18 papers. Outputs in `runs/smoke/` |
| `configs/pipeline.smoke20.yaml` | Test run of about 20 papers (up to 24). Outputs in `runs/smoke20/` |
| `configs/pipeline.smoke30.yaml` | Test run of about 30 papers (up to 36). Outputs in `runs/smoke30/` |
| `pipeline.yaml` | Your full run. Copy it from `configs/pipeline.example.yaml` |

## Setup (once)

| Command | What it does |
|---|---|
| `uv sync` | Installs everything |
| `uv run python -m spacy download en_core_web_lg` | Downloads the model used to find personal data |
| `cp .env.example .env` | Creates the file for your API key |
| `docker compose up -d` | Windows only: starts Milvus (see README, Install) |

## Run the pipeline

`uv run chitchat run` runs every stage in order. To run some stages only:
`uv run chitchat run --stages screen,export`

| Stage | What it does |
|---|---|
| `queries` | Builds the boolean search from the synonyms and categories. Offline |
| `discover` | Searches OpenAlex, Europe PMC and arXiv, and downloads PDFs |
| `ingest` | Reads your own documents from `my_docs/`. Skipped if the folder is missing |
| `sanitize` | Masks personal data. No LLM, nothing leaves your machine |
| `screen` | The LLM answers the criteria. Rules decide the label. Finished papers are reused |
| `export` | Writes `dataset.csv`, `dataset.jsonl`, `sources.json` and the PRISMA report |
| `index` | Puts the included papers and your documents into Milvus |

## Other commands

| Command | What it does |
|---|---|
| `uv run chitchat ask "question"` | Answers from the index, citing `[P0001]` tags |
| `uv run chitchat ask --no-privacy "question"` | Same, without privacy mode |
| `uv run chitchat ask --review "question"` | Lets you check the context before it is sent |
| `uv run chitchat status` | Shows which stages are done and what they produced |
| `uv run chitchat report` | Rebuilds the dataset and PRISMA report |
| `uv run chitchat run --redecide` | Relabels papers with the current rules. No LLM calls |

## Examples

```powershell
# About 30 papers, start to finish
uv run chitchat run -c configs/pipeline.smoke30.yaml
uv run chitchat ask -c configs/pipeline.smoke30.yaml "What consent practices do the papers describe?"

# Changed the decision rules only
uv run chitchat run -c configs/pipeline.smoke30.yaml --redecide
uv run chitchat report -c configs/pipeline.smoke30.yaml
```

## Development

| Command | What it does |
|---|---|
| `uv run pytest` | Fast tests. No network, models or API keys |
| `uv run pytest -m slow` | A tiny real run, end to end |
| `uv run ruff check .` | Lint |
| `uv run ruff format .` | Format |
