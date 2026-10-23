# How the pipeline works

This page explains what happens when you run each command: what it reads, what it writes, what it skips or reuses, and what to rerun after you change something. For a short list of the commands, see [COMMANDS.md](COMMANDS.md).

## The big picture

```
synonyms + categories ──► queries ──► discover ──► sanitize ──► screen ──► export ──► index ──► ask
                                                     ▲
                                my_docs/ ──► ingest ─┘   (own documents skip screen and go to export/index)
```

- **One config file drives a run.** It names the run (`run_name`) and points to the other configs.
- **Each stage reads files and writes files** in `runs/<run_name>/`. You can rerun any stage on its own.
- **Raw text stays in `runs/<run_name>/raw/`.** Every file outside `raw/` holds sanitized text only.

## What happens before any stage runs

Every `chitchat` command does these steps first, in this order:

1. **Restarts itself once** with two settings:
   - a fixed hash seed, so mmore's chunk ids are stable;
   - UTF-8 mode, so the Windows console can print every character.

   You won't notice this restart.
2. **Hides library warnings.** These are deprecation notices from LangChain, torch and others.
3. **Checks your API keys.** If an `*_API_KEY` is set in your environment *and* in `.env` with a different value, it warns you. The environment value wins, because `.env` never overrides it.
4. **Loads `.env`.**
5. **Checks all config files**, before any network or LLM call:
   - **the pipeline config:** required keys, unknown keys, file paths, labels and the run name;
   - **the criteria file:** ids, types, scales and rules;
   - **the sanitize config:** every privacy setting must be set, so no LLM is ever asked to choose one.

   Any problem stops the command with a message that names the field at fault (exit code 2).

## `chitchat search`: planning the search

`chitchat search "question"` builds the boolean search from your question instead of the predefined files. It then sets up a new run folder and runs the pipeline there.

1. **Run folder.** A new folder named from the question and the date, e.g. `runs/humanitarian-organisations-obtain-informed-consent-2026-10-21/`. If it exists, `-2`, `-3`… is added. `--run-name` sets the name yourself.
2. **Privacy check.** Your question, and later your answers and change requests, are checked for personal data on your machine with Presidio (the `rag_privacy.yaml` settings). Anything found is masked before it goes to the LLM, and you see the masked version.
3. **Clarifying questions (deep mode only).** The LLM asks about 4 questions: scope, population, setting, years, what to leave out. Each has suggested answers. Type a number, your own answer, or press Enter to skip.
4. **Draft.** The LLM proposes concepts (each with synonyms) and categories (each combining 2 or more concepts with AND). If the draft breaks the rules, for example a category with only one concept, the LLM is asked to fix it, up to 2 times, before you see it.
5. **Checks on the draft.** Terms are cleaned (no quotes or AND/OR inside), duplicates and unknown words are dropped, and the mode's limits are applied. If a query is over 1,500 characters, the last synonyms of its longest group are dropped until it fits, so OpenAlex can run it. Every change is listed under the draft.
6. **What you see.** A summary line (number of categories and concepts, and how many fit OpenAlex), then one box per category:

   ```
   ╭─ Category 1 · Consent in data collection ────────────────────────────────╮
   │ informed consent  or: data permission, opt-in consent, explicit consent  │
   │ AND                                                                      │
   │ data collection   or: data gathering, data acquisition                   │
   ╰─────────────────────────────────────────── 194 characters · OpenAlex ok ─╯
   ```

   - Each line is one concept: the concept itself, then `or:` and its synonyms. A paper matches the line if it uses any of them.
   - `AND` between lines means a paper must match every line of the box.
   - Each concept keeps the same colour in every box, so you can see when two categories share one.
   - The bottom border shows the query's length and whether OpenAlex accepts it.
7. **Your decision.** `a` accepts. `c` asks for a change in plain words: the LLM revises the whole search with the full conversation, and you see the new draft. Repeat as often as you like. `q` quits and saves nothing.
8. **Saved files.** `search/synonyms.jsonl`, `search/categories.yaml` and `search/discovery.yaml` (in mmore's formats), `search/plan.json` (the whole conversation: question, answers, every draft and change request), and `pipeline.yaml` (your template settings, pointed at this folder, with its own Milvus collection).
9. **Run.** It asks "Run the pipeline now?" and runs every stage. Later commands use `-c runs/<folder>/pipeline.yaml`.

| | Shallow: quick scan | Deep: systematic search (default) |
|---|---|---|
| Clarifying questions | none | 4 |
| Categories | 1 to 3 | 3 to 6 |
| Concepts per category | 2 to 4 | 2 to 4 |
| Synonyms per concept | up to 5 | up to 8 |
| Results | 10 per source, 1 page | 25 per source, 2 pages |
| PDFs | not downloaded: screening reads abstracts | downloaded: screening reads full text |

Change any of these under `search.shallow` or `search.deep` in your pipeline config. Only the fields you set are changed. `search.mode` sets the default mode, and `search.llm` the model (default: the screening model).

`--predefined` skips the planning and uses the search files named in the config (`discovery.config`). It still gets a new folder, timing and history.

### Choosing sources

Every search goes to **OpenAlex, Europe PMC and arXiv** by default. The draft's summary line names the sources it will search. The "OpenAlex ok / too long" status appears only because OpenAlex is the one source with a length limit (1,500 characters). Europe PMC and arXiv have no such limit to check.

| Source | Covers | Notes |
|---|---|---|
| `openalex` | Most fields, all publishers | Rejects queries over 1,500 characters. Drafts are fitted to it automatically |
| `europepmc` | Life sciences and health | |
| `arxiv` | Computer science, physics, statistics preprints | Searches key terms, not the full boolean |
| `google_scholar` | Everything | Off by default. Needs the extra `mmore[google_scholar]` (Selenium) and often hits captchas |

Where to change them:

- **For new searches:** in your template config, list the sources per mode. Only the modes you change are affected:

  ```yaml
  search:
    deep:
      sources: [openalex, europepmc]
    shallow:
      sources: [arxiv]
  ```

  Without OpenAlex in the list, queries are not trimmed and the OpenAlex status is not shown.
- **For one run that's already planned:** edit `sources:` in `runs/<folder>/search/discovery.yaml`, then rerun from `discover`: `uv run chitchat run -c runs/<folder>/pipeline.yaml`.
- **For the predefined search:** edit `sources:` in `configs/discovery/discovery.yaml`.

## `chitchat run`

```bash
uv run chitchat run -c <config>                       # every stage
uv run chitchat run -c <config> --stages screen,export
uv run chitchat run -c <config> --redecide
```

- **Order:** stages always run in pipeline order, whatever order you type them in.
- **Errors:** if a stage fails, the run stops there. Later stages don't run, and earlier results are kept.
- **Done markers:** after each successful stage, a marker is written to `runs/<run>/.done/<stage>`. `chitchat status` shows these. **Nothing is ever skipped because of a marker.** A stage runs every time you ask for it.
- **`--redecide`** ignores `--stages` and only relabels screened papers (see [screen](#5-screen)).

## Runs, history and logs

Every command that runs stages (`run`, `report`, `search`) is one run, with an id like `2026-10-21T14-03-07`.

- **In the terminal:** each stage header shows its start time, each stage ends with how long it took, and the run ends with a Done, Failed or Interrupted box listing every stage's duration, the total, the run id and the log file.
- **`history.jsonl`:** one line per run in the run folder: run id, command, config, mode, start and end, outcome, any error, and each stage's start, duration and outcome. It is written even when a stage fails or you press Ctrl+C.
- **`logs/<run id>.log`:** everything the run printed, with a short header. Progress bars are left out, so it stays readable.
- **`chitchat status`:** a "Took" column with each stage's last duration, and a table of the 5 most recent runs.

## The stages

### 1. `queries`

Builds the boolean search. **Offline, no network.**

- **Reads:**
  - the discovery config, e.g. `configs/discovery/discovery.yaml`;
  - its synonyms file and categories file. Their paths are relative to the discovery config.
- **Does:**
  - turns each word and its synonyms into a quoted `OR` group: `("AI" OR "machine learning" OR …)`;
  - joins the groups of each category with `AND`;
  - drops a word that isn't in the synonyms file, with a warning.
- **Shows** a table with one row per category: its concepts (joined by AND), the number of AND groups, the length in characters, and whether OpenAlex accepts it.
- **Writes:** `queries.json`, one entry per category: its name, its concepts and the full query. It is replaced each time.
- **Warns** when a query is over 1,500 characters and OpenAlex is a source. OpenAlex rejects those, so it returns nothing for that category.
- **Optional:** `discover` builds the same queries itself. This stage is for looking at them before you search.

### 2. `discover`

Searches the sources and downloads PDFs. **Needs the network.** This is the slowest stage.

- **Reads:** the same discovery config.
- **Does:**
  1. Runs every category's query on every source in `sources`: OpenAlex, Europe PMC, arXiv.
     - Each source returns at most `max_results` papers per category.
     - A source that fails logs a warning and returns nothing. The run continues.
  2. Removes duplicates across sources and categories.
  3. Downloads each PDF and extracts its text with PyMuPDF (`pdf_extractor: fast`).
- **Writes, all in `raw/`:**
  - `papers.jsonl`: all papers, with their text. Replaced each time.
  - `discovery_stats.json`: counts per source, duplicates, PDF outcomes. Used for PRISMA.
  - `papers_failed_pdfs.csv`: PDFs that couldn't be downloaded, each with a `save_as` path.
  - `pdfs/`: the downloaded PDFs.
- **Reuses:**
  - **PDFs** already in `raw/pdfs/` (`pdf_status: cached`), so a rerun doesn't download them again.
  - **Manual downloads:** save a PDF at its `save_as` path and rerun `discover`. It's picked up.
- **Not reused: the paper list itself.** The sources are live, so a rerun can return different papers.
- **Ctrl+C** stops the search but still writes what was found so far.

### 3. `ingest`

Reads your own documents: reports, notes, PDFs, Word files and more.

- **Skipped** if `own_documents.folder` is unset or the folder doesn't exist. That isn't an error.
- **Reads:** every file in the folder, with mmore process. `fast: true` avoids OCR models.
- **Writes, in `raw/`:**
  - `docs.jsonl`, with a stable `doc_id` for each file: a hash of the file's bytes, so a renamed file keeps its id. Replaced each time.
  - `docs_process/`: mmore's working files.
- **Own documents are never screened.** They go to `sanitize`, then `export` (for their `D0001` tags), then `index`.

### 4. `sanitize`

Masks personal data. **No LLM. Nothing leaves your machine.**

- **Reads:** `raw/papers.jsonl` and, if it exists, `raw/docs.jsonl`. If there are no papers yet, it says so and does the documents only.
- **Does:**
  - finds names, emails and similar with Presidio (spaCy), using the settings in `configs/sanitize.yaml`;
  - replaces each one with a token: `[PERSON_1]`, `[EMAIL_ADDRESS_2]`, …;
  - the same value gets the same token within one document;
  - uses **two different lists** of what to mask:
    - **Papers:** names, emails and SSNs. Places, dates and numbers are kept, because they are research content. Phone numbers are also kept: Presidio is unsure about them (score 0.4), and papers use a 0.7 cut-off so figures in tables aren't mistaken for phone numbers.
    - **Own documents:** also phone numbers (0.4 cut-off), locations, dates, medical record and insurance ids.
  - splits an email from a footnote number stuck to it (`a@b.com2` → `a@b.com 2`), so the email is found.
- **Writes:**
  - `papers.sanitized.jsonl`: each paper with its abstract and text masked, plus its `paper_id` and a per-paper privacy count. Replaced each time.
  - `docs.sanitized.jsonl`: the same for your documents.
  - `privacy_report.json`: totals per kind of personal data. Counts only, never the values.
- **Reuses nothing:** it redoes every document each time. Presidio is slow on long texts, so expect minutes.
- **Expect some over-masking.** Authors in reference lists are masked, and some product names may be too.

### 5. `screen`

An LLM answers your criteria for each paper. Fixed rules then decide the label.

- **Reads:**
  - `papers.sanitized.jsonl`. If `privacy.before_screening` is `false`, it reads the raw papers instead, with a warning.
  - the criteria file;
  - `screening.jsonl`, to reuse earlier results.
- **For each paper, in this order:**
  1. **Already done?** A paper is reused, with no LLM call, when an earlier record has the same `paper_id`, the same criteria hash and the same model, **and** its status is `screened` or `skipped`.
  2. **Too old?** If `year` < `min_year`, it's skipped as `before_min_year`. Papers with no year are not skipped.
  3. **Which text to send:**
     - **Full text**, if it's at least `min_chars` long. If it's longer than `max_chars`, the first 70% and last 30% of the budget are kept.
     - **Otherwise the abstract**, if `use_abstract_if_no_text` is on and the abstract is at least 300 characters. This is a weaker screening.
     - **Otherwise skipped:** `no_text` if there's no text at all, or `text_too_short`.
  4. **Ask the LLM** the criteria. Each answer comes with a short evidence quote.
  5. **Apply the rules.** The first rule that matches gives the label: `EXCLUDE`, `LOW`, `MEDIUM` or `HIGH`.
  6. **Extract** the `extract:` fields (datasets, languages, …), only for papers that aren't `EXCLUDE`. This is a second LLM call.
- **Writes:** one line per paper in `screening.jsonl`, appended as soon as that paper is done. Several papers run at once (`max_concurrency`).
- **Paper outcomes:**

  | Status | Meaning | Next run |
  |---|---|---|
  | `screened` | Answered and labelled | Reused |
  | `skipped` | Not sent to the LLM (too old, no text, too short) | Reused |
  | `refused` | The model refused | Retried |
  | `invalid` | The answer didn't fit the format | Retried |
  | `error` | The call failed (network, rate limit, …) | Retried |

- **Stops the whole stage** on a bad API key or an unknown model, because every paper would fail. Finished papers are kept. The message says if an old key in your environment is overriding `.env`.
- **The criteria hash** covers the questions, the scales and the extract fields, but **not the rules**. So:
  - **you change a question, scale or extract field:** the hash changes, and every paper is screened again;
  - **you change only the rules:** the hash stays the same. Use `--redecide`.
- **`--redecide`** recomputes the label of every `screened` paper from its stored answers, with the current rules. **No LLM calls.** It rewrites `screening.jsonl`.
- **A different model** (`screening.llm.llm_name`) screens every paper again. Results from the old model stay in the file.

### 6. `export`

Builds the dataset and the PRISMA report. **No network.**

- **Reads:**
  - `papers.sanitized.jsonl`. This one is required.
  - the latest record per paper in `screening.jsonl`;
  - `docs.sanitized.jsonl`;
  - `raw/discovery_stats.json`.
- **Writes:**
  - `sources.json`: a short tag for every paper (`P0001`, …) and document (`D0001`, …), numbered in order of their ids.
  - `dataset.jsonl`: each sanitized paper with its screening result. Papers without a record show `not_screened`.
  - `dataset.csv`: one row per paper and one column per criterion and extract field. It opens cleanly in Excel.
  - `prisma.json` and `prisma.md`: the PRISMA flow, every number computed from the files.
- **Checks** that the PRISMA boxes add up, and warns if they don't. That usually means `discover` was rerun without `sanitize`.
- **Everything is replaced each time.** `chitchat report` runs this stage only.
- **Tags can change.** If the set of papers changes, the numbering can shift, and a tag in an old answer may then point to a different paper.

### 7. `index`

Puts the included papers and your documents into Milvus, so `ask` can search them.

Where Milvus is depends on `index.db_uri`:

| `db_uri` | Windows | macOS and Linux |
|---|---|---|
| `auto` (the default) | Milvus in Docker at `http://127.0.0.1:19530` | Milvus Lite: a `milvus.db` file in the run folder, no server |
| `http://…` | that Milvus server | that Milvus server |
| a file path | not possible: Milvus Lite has no Windows build | that file |

Each run folder from `chitchat search` gets its own collection, so runs never overwrite each other's index.

- **Reads:** `sources.json` (run `export` first), the sanitized papers and documents, and `screening.jsonl`.
- **Chooses:**
  - papers whose label is in `index.include_labels` (default HIGH, MEDIUM, LOW). Each uses its full text, or its abstract if there's no full text.
  - your documents too, if `include_own_documents` is on.
- **Does:**
  1. Splits the texts into chunks of a few sentences.
  2. Starts every chunk with its tag, e.g. `[P0007] …`, so the answer can cite it.
  3. Creates the Milvus database (`db_name`) if needed. Milvus Lite always uses its default database.
  4. **Deletes the old collection and builds it again.** The index always matches the current results.
- **Fails clearly** when nothing is included ("Run screen first") or Milvus can't be reached ("Is Milvus running?").
- **The first run downloads embedding models** (about 600 MB).

## `chitchat ask`

```bash
uv run chitchat ask -c <config> "question"
uv run chitchat ask -c <config> --no-privacy "question"
uv run chitchat ask -c <config> --review "question"
uv run chitchat ask -c <config> --k 10 "question"
```

1. **Finds** the `k` chunks closest to your question in Milvus (default 6, or `--k`).
2. **Privacy mode** is on when `privacy.rag_privacy_config` is set and you didn't pass `--no-privacy`:
   - the chunks and your question are checked for personal data and masked again before the LLM sees them;
   - it answers with the model in `configs/rag_privacy.yaml` (`answer.llm`);
   - **`--review`** shows you the masked context and waits for your approval before anything is sent.
3. **Without privacy mode**, it answers with `ask.llm` from the pipeline config.
4. **Prints:**
   - the answer;
   - the sources it cited: tag, title, year, DOI or link;
   - if the model cited nothing, the papers it was given, under "Sources (retrieved, not cited by the model)";
   - a one-line privacy summary: what was masked in your question and in the retrieved text.
5. **Appends** the question, the answer and the sources to `answers.jsonl`.

Things to know:

- **Your question can be masked.** Privacy mode can mistake a product or project name for a person. When your question was changed, `ask` shows the version it sent. Rephrase it ("the MoodSmith system") or use `--no-privacy`.
- **Aborted answers.** If the leakage check is on in `rag_privacy.yaml` and it fails, there is no answer. You'll see "the privacy check stopped it".
- **"The context does not answer the question"** usually means none of the indexed papers covers it. The sources list then shows what it was given.

## `chitchat status` and `chitchat report`

- **`status`** shows, for each stage, whether it has run, when, and what it produced. It only reads files.
- **`report`** runs `export` again. Use it after `--redecide`, or after a new `screen`.

## What to rerun after a change

| You changed… | Run | Notes |
|---|---|---|
| Synonyms, categories or discovery settings | `queries`, `discover`, `sanitize`, `screen`, `export`, `index` | Papers already screened are reused |
| Saved missing PDFs at their `save_as` paths | `discover`, `sanitize`, `screen`, `export`, `index` | See "Known gaps" |
| A question, scale or extract field in the criteria | `screen`, `export`, `index` | Every paper is screened again |
| Only the rules in the criteria | `run --redecide`, then `report`, then `index` | No LLM calls |
| The screening model | `screen`, `export`, `index` | Every paper is screened again |
| `min_year`, `min_chars` or `use_abstract_if_no_text` | `screen`, `export`, `index` | See "Known gaps" |
| Files in `my_docs/` | `ingest`, `sanitize`, `export`, `index` | Documents are never screened |
| `configs/sanitize.yaml` | `sanitize`, `export`, `index` | Screening is not redone |
| `index.include_labels` or the embedding model | `index` | |
| `configs/rag_privacy.yaml` or `ask` settings | nothing | Applies to the next `ask` |

## Known gaps

- **Screening criteria don't follow the question.** `chitchat search` builds the search from your question, but screening still uses `configs/criteria.example.yaml`, which is written for humanitarian AI data ethics.
- **Skipped papers stay skipped.** A `skipped` record counts as finished. If you lower `min_year`, lower `min_chars`, or add a PDF for a paper skipped as `no_text`, it is not screened again. To redo those papers, delete their lines from `screening.jsonl` and run `screen`. To redo everything, delete the whole file.
- **Screening ignores new text.** A paper screened on its abstract keeps that result after you add its PDF. The fix is the same: delete its line.
- **Sanitize changes don't reach screening.** After you change `sanitize.yaml`, the masked text changes, but screened papers are reused.
- **OpenAlex drops long queries.** Queries over 1,500 characters return nothing from OpenAlex. `queries` and `discover` warn you. The full category set is over this limit, so a full run gets nothing from OpenAlex until the synonyms are shortened.

## The run folder

```
runs/<run_name>/
├── pipeline.yaml               search: this run's config (use it with -c)
├── search/                     search: synonyms.jsonl, categories.yaml, discovery.yaml, plan.json
├── history.jsonl               one line per run: stages, durations, outcome
├── logs/                       one log file per run
├── raw/                        raw text: never share this folder
│   ├── papers.jsonl            discover
│   ├── discovery_stats.json    discover
│   ├── papers_failed_pdfs.csv  discover (missing PDFs, with save_as paths)
│   ├── pdfs/                   discover
│   ├── docs.jsonl              ingest
│   └── docs_process/           ingest (mmore working files)
├── queries.json                queries
├── papers.sanitized.jsonl      sanitize
├── docs.sanitized.jsonl        sanitize
├── privacy_report.json         sanitize
├── screening.jsonl             screen (appended; one line per paper per attempt)
├── sources.json                export (tags)
├── dataset.jsonl               export
├── dataset.csv                 export
├── prisma.json, prisma.md      export
├── index/chunks.jsonl          index
├── answers.jsonl               ask (appended)
└── .done/                      stage markers, for status only
```
