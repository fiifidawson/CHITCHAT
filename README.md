# CHITCHAT

*ArCHitectures for Interpretable & Transparent Continuous Humanitarian Alignment in chatbot Technologies*

CHITCHAT is a literature-review pipeline built on [mmore](https://github.com/EPFLiGHT/mmore). You ask a research question. It:

1. turns your question into a boolean search, which you check and refine;
2. finds papers in OpenAlex, Europe PMC and arXiv, and reads your own documents;
3. masks personal data, on your machine, before anything is sent to an LLM;
4. screens each paper against your criteria, with evidence quotes;
5. writes a dataset and a PRISMA report;
6. answers questions with cited sources, like `[P0012]` for a paper or `[D0003]` for one of your documents.

It is a research project of the LiGHT lab at EPFL, with the ICRC.

> [!IMPORTANT]
> Screening is an aid, not a final decision. Every label comes with evidence quotes so a person can check it.

## Documentation

| Read this | When you want to |
|---|---|
| [docs/SETUP.md](docs/SETUP.md) | Install everything, step by step, on Windows or macOS |
| [examples/README.md](examples/README.md) | Try three end-to-end examples, from 3 minutes to 45 minutes |
| [docs/COMMANDS.md](docs/COMMANDS.md) | Look up a command |
| [docs/PIPELINE.md](docs/PIPELINE.md) | Understand what each stage does, skips and reuses |
| [docs/USE_CASES.md](docs/USE_CASES.md) | See what the pipeline is for, with fictional sample documents |

## Quick start

After [setup](docs/SETUP.md):

```bash
uv run chitchat search "How do humanitarian organisations obtain informed consent when collecting data to train LLMs?"
```

1. **Clarifying questions.** Answer a few questions about scope. Press Enter to skip one.
2. **Your search.** You see the drafted search, one box per category:

   ```
   ╭─ Category 2 · Consent for LLM training data ─────────────────────────────╮
   │ informed consent       or: data permission, opt-in consent, user consent │
   │ AND                                                                      │
   │ large language models  or: LLMs, language models, generative AI          │
   │ AND                                                                      │
   │ data collection        or: data gathering, data acquisition              │
   ╰─────────────────────────────────────────── 274 characters · OpenAlex ok ─╯
   ```

   A paper must match every concept in a category (`AND`), through the concept or any of its synonyms (`or:`).
3. **Your decision.** Type `a` to accept, `c` to ask for changes in plain words (for example "add a category on community participation"), or `q` to quit. Ask for changes as often as you like.
4. **The run.** It runs in a new folder in `runs/`. Then ask questions:

```bash
uv run chitchat ask -c runs/<folder>/pipeline.yaml "What consent practices do the papers describe?"
```

## Two search modes

| | Shallow: quick scan | Deep: systematic search (default) |
|---|---|---|
| Use it for | A fast look at what exists | A thorough search for a review |
| Clarifying questions | none | 4, before drafting |
| Categories | 1 to 3 | 3 to 6 |
| Concepts per category | 2 to 4 | 2 to 4 |
| Results | 10 per source | 25 per source, 2 pages |
| Full text | no: screens abstracts, so it takes minutes | yes: downloads PDFs |

Choose with `--mode shallow` or `--mode deep`. The fixed search from the earlier project is still available with `--predefined`.

## The pipeline

| # | Stage | What it does | Main output in `runs/<folder>/` |
|---|---|---|---|
| 1 | `queries` | Builds the boolean queries. Offline | `queries.json` |
| 2 | `discover` | Searches OpenAlex, Europe PMC and arXiv, downloads PDFs | `raw/papers.jsonl` |
| 3 | `ingest` | Reads your own documents (PDF, Word, Excel, email, web pages, text) | `raw/docs.jsonl` |
| 4 | `sanitize` | Masks names, emails, phone numbers and more. No LLM | `papers.sanitized.jsonl`, `privacy_report.json` |
| 5 | `screen` | An LLM answers your criteria. Fixed rules decide the label | `screening.jsonl` |
| 6 | `export` | Dataset and PRISMA report | `dataset.csv`, `prisma.md` |
| 7 | `index` | Puts included papers and your documents into a search index | a Milvus collection |
| – | `ask` | Answers a question with citations | `answers.jsonl` |

Every run records its stages, durations and outcome in `history.jsonl`, and its full output in `logs/`. `chitchat status` shows both.

## Configuration

| File | What it sets |
|---|---|
| `runs/<folder>/pipeline.yaml` | One run: written by `chitchat search` from your template |
| `pipeline.yaml` (your template) | Models, privacy, screening and index settings. Copy it from `configs/pipeline.example.yaml` |
| `configs/criteria.example.yaml` | Screening questions and decision rules |
| `configs/sanitize.yaml` | Which personal data is masked, for papers and for your documents |
| `configs/rag_privacy.yaml` | Privacy checks when answering questions |
| `configs/discovery/` | The predefined search (`--predefined`): synonyms, categories, sources |

## Privacy

- Your question, your answers and your change requests are checked for personal data on your machine before they reach an LLM.
- Raw text stays in `runs/<folder>/raw/`. Do not share that folder. Everything else holds masked text only.
- Your own documents are always masked, with a broader list than papers (papers keep places and dates, which are research content).
- Masking lowers risk but does not guarantee anonymity. See [docs/USE_CASES.md](docs/USE_CASES.md) for what it misses.

## Known limits

- **Screening criteria** are written for humanitarian AI data ethics. A search on another topic still uses them: edit `configs/criteria.example.yaml` to change them.
- **PDFs:** publishers refuse many downloads. Missing ones are listed in `raw/papers_failed_pdfs.csv`, where you can add them by hand.
- **OpenAlex** rejects queries over 1,500 characters. Searches from `chitchat search` are fitted automatically. The predefined search is too long for it.
- **Costs:** one LLM call per paper to screen it, one more for papers that are not excluded, and one per question. A small run costs cents.
- **Windows:** the search index needs Docker. macOS and Linux don't.

## Development

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest            # no network, models or API keys
uv run pytest -m slow    # a tiny real run, using your API key and Milvus
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
