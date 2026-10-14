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

## `chitchat run`

```powershell
uv run chitchat run -c <config>                       # every stage
uv run chitchat run -c <config> --stages screen,export
uv run chitchat run -c <config> --redecide
```

- **Order:** stages always run in pipeline order, whatever order you type them in.
- **Errors:** if a stage fails, the run stops there. Later stages don't run, and earlier results are kept.
- **Done markers:** after each successful stage, a marker is written to `runs/<run>/.done/<stage>`. `chitchat status` shows these. **Nothing is ever skipped because of a marker.** A stage runs every time you ask for it.
- **`--redecide`** ignores `--stages` and only relabels screened papers (see [screen](#5-screen)).

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
- **Writes:** `queries.json`, one query per category. It is replaced each time.
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
    - **Papers:** names, emails, phone numbers, SSNs. Places and dates are kept, because they are research content.
    - **Own documents:** also locations, dates, medical record and insurance ids.
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

- **Reads:** `sources.json` (run `export` first), the sanitized papers and documents, and `screening.jsonl`.
- **Chooses:**
  - papers whose label is in `index.include_labels` (default HIGH, MEDIUM, LOW). Each uses its full text, or its abstract if there's no full text.
  - your documents too, if `include_own_documents` is on.
- **Does:**
  1. Splits the texts into chunks of a few sentences.
  2. Starts every chunk with its tag, e.g. `[P0007] …`, so the answer can cite it.
  3. Creates the Milvus database if needed.
  4. **Deletes the old collection and builds it again.** The index always matches the current results.
- **Fails clearly** when nothing is included ("Run screen first") or Milvus can't be reached ("Is Milvus running?").
- **The first run downloads embedding models** (about 1 GB).

## `chitchat ask`

```powershell
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
   - a one-line privacy summary.
   - If nothing was cited, it lists the papers it retrieved.
5. **Appends** the question, the answer and the sources to `answers.jsonl`.

Things to know:

- **Your question can be masked.** Privacy mode can mistake a product or project name for a person. When your question was changed, `ask` shows the version it sent. Rephrase it ("the MoodSmith system") or use `--no-privacy`.
- **Aborted answers.** If the leakage check is on in `rag_privacy.yaml` and it fails, there is no answer. You'll see "the privacy check stopped it".
- **"The context does not answer the question"** usually means none of the indexed papers covers it. The `Retrieved:` line shows what was searched.

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

- **Skipped papers stay skipped.** A `skipped` record counts as finished. If you lower `min_year`, lower `min_chars`, or add a PDF for a paper skipped as `no_text`, it is not screened again. To redo those papers, delete their lines from `screening.jsonl` and run `screen`. To redo everything, delete the whole file.
- **Screening ignores new text.** A paper screened on its abstract keeps that result after you add its PDF. The fix is the same: delete its line.
- **Sanitize changes don't reach screening.** After you change `sanitize.yaml`, the masked text changes, but screened papers are reused.
- **OpenAlex drops long queries.** Queries over 1,500 characters return nothing from OpenAlex. `queries` and `discover` warn you. The full category set is over this limit, so a full run gets nothing from OpenAlex until the synonyms are shortened.

## The run folder

```
runs/<run_name>/
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
