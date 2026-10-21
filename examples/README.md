# Examples

Three end-to-end examples, each with its own config in this folder. Run every command from the repo root.

| Example | What it shows | Time | LLM cost |
|---|---|---|---|
| [Thorough: deep search and your documents](#thorough-deep-search-and-your-documents) | The whole pipeline: clarifying questions, a change request, papers and documents together, privacy checks, relabelling, run history | 30 to 45 min | about $0.10 to $0.30 |
| [Minor 1: quick scan](#minor-1-quick-scan) | A shallow search on abstracts, then a few questions | 5 to 10 min | under $0.05 |
| [Minor 2: your documents only](#minor-2-your-documents-only) | No paper search: read, mask, index and question the sample documents | about 3 min | under $0.01 |

The sample documents in [my_docs/](my_docs/) are fictional: the organisation, people, phone numbers, emails and IDs are made up. See [docs/USE_CASES.md](../docs/USE_CASES.md) for what each one contains.

## Before you start (once)

```powershell
uv sync
uv run python -m spacy download en_core_web_lg
docker start milvus-etcd milvus-minio milvus-standalone     # or follow "Milvus" in the README
Remove-Item Env:OPENAI_API_KEY -ErrorAction SilentlyContinue  # so the key in .env is used
```

Check that `.env` has a working `OPENAI_API_KEY`, and that `docker ps` shows `milvus-standalone` as healthy. The configs use Milvus at `http://127.0.0.1:19530`. On Linux or macOS you can set `index.db_uri: milvus.db` instead.

## Thorough: deep search and your documents

Config: [thorough/pipeline.yaml](thorough/pipeline.yaml). Deep mode with 8 results per source and category, plus the 7 sample documents.

### 1. Plan the search

```powershell
uv run chitchat search -c examples/thorough/pipeline.yaml "How do humanitarian organisations obtain and manage informed consent when collecting data to train or fine-tune large language models?"
```

1. **Clarifying questions.** Try each kind of answer: type `1` to pick the first suggestion, type a sentence such as `since 2018, peer-reviewed and grey literature`, and press Enter on one to skip it.
2. **First draft.** You see a Concepts table and a Boolean queries table. Check that every query says `ok` under OpenAlex.
3. **Ask for a change.** Type `c`, then: `add a category on community participation and the right to opt out, and drop generic machine learning terms`. The new draft should have that category, and fewer broad synonyms.
4. **Accept.** Type `a`. A **Search ready** box shows the new run folder, e.g. `runs/humanitarian-organisations-obtain-manage-informed-consent-2026-10-21/`.
5. **Run.** Answer `y` to "Run the pipeline now?".

### 2. Watch the run

Each stage starts with a yellow header and its start time, and ends with "finished in …". What to look for:

| Stage | What you should see |
|---|---|
| queries | One row per category, all `ok` for OpenAlex |
| discover | The Discovery box: papers per source (OpenAlex now included), PDFs downloaded or refused |
| ingest | The Own documents box: 7 documents |
| sanitize | The Privacy box: names, emails, phone numbers, dates and places masked, "No LLM was used" |
| screen | One line per paper with HIGH, MEDIUM, LOW, EXCLUDE or SKIPPED and the reason, then the summary box with token counts |
| export | The Dataset and PRISMA box |
| index | The Index box: papers, 7 own documents, chunks |
| end | The Done box: every stage's duration, the run id and the log file |

From here on, `<run>` means your run folder, e.g. `runs/humanitarian-organisations-obtain-manage-informed-consent-2026-10-21`.

### 3. Ask questions

```powershell
uv run chitchat ask -c <run>/pipeline.yaml "<question>"
```

Papers and your documents together. Answers should cite `[P…]` tags for papers and `[D…]` tags for documents.

- "What consent practices do the papers describe for data used to train language models?"
- "How does the consent approach agreed in Kakuma compare with what the papers recommend?"
- "What did our working group decide about using helpline transcripts, and why?"
- "Which risks of re-identification do the papers and our documents mention?"
- "Which of our datasets are on hold or excluded, and what would make them usable?"
- "Why did the medical coordinator advise against using health calls?"

### 4. Check privacy

```powershell
uv run chitchat ask -c <run>/pipeline.yaml "Who wrote the field visit notes, and what is their phone number?"
uv run chitchat ask -c <run>/pipeline.yaml "I'm Kwame Asante (kwame.asante@example.org, +44 20 7946 0958). What does our policy say about external language model APIs?"
uv run chitchat ask -c <run>/pipeline.yaml --no-privacy "What does our policy say about external language model APIs?"
uv run chitchat ask -c <run>/pipeline.yaml --review "What does our consent form say about withdrawing?"
```

- The first answer shows only `[PERSON_n]` and `[PHONE_NUMBER_n]`, never the real values.
- The second shows "Privacy mode sent your question as: I'm [PERSON_1] ([EMAIL_ADDRESS_1], [PHONE_NUMBER_1])…" and "question: 3 masked".
- The third has no privacy line.
- The fourth pauses and shows you the masked context before anything is sent.

### 5. Look at the outputs

| File in `<run>/` | What to check |
|---|---|
| `prisma.md` | The flow from papers found to papers included. The numbers add up |
| `dataset.csv` | Open in Excel. Read the evidence columns for a few HIGH and EXCLUDE papers: do you agree? |
| `privacy_report.json` | How much was masked, for papers and for own documents |
| `docs.sanitized.jsonl` | The masked text of the sample documents. `MRN 448-1207` is expected to remain |
| `search/plan.json` | Your question, answers, every draft and your change request |
| `history.jsonl`, `logs/` | One line and one log file per run |

```powershell
uv run chitchat status -c <run>/pipeline.yaml
```

The status table has a "Took" column, and a Recent runs table lists your runs.

### 6. Change the rules without paying again

1. In `configs/criteria.example.yaml`, make the HIGH rule stricter, for example add `ethical_framework == yes` to its `when:` list.
2. Relabel and rebuild the report, with no LLM calls:

```powershell
uv run chitchat run -c <run>/pipeline.yaml --redecide
uv run chitchat report -c <run>/pipeline.yaml
uv run chitchat run -c <run>/pipeline.yaml --stages index
```

The Relabelled box says how many labels changed. `prisma.md` has the new numbers, and `index` rebuilds the index with the new set of included papers. Undo your edit afterwards.

### 7. Rerun and see what is reused

```powershell
uv run chitchat run -c <run>/pipeline.yaml --stages screen
```

It screens nothing new: every paper is reused from the first run. The Recent runs table in `status` now shows this run too.

## Minor 1: quick scan

Config: [quick-scan/pipeline.yaml](quick-scan/pipeline.yaml). Shallow mode: one category, 10 results per source, abstracts only, no own documents.

```powershell
uv run chitchat search -c examples/quick-scan/pipeline.yaml "Which methods are used to reduce bias when collecting training data for language models in low-resource languages?"
```

1. No clarifying questions in shallow mode. You see one query with 3 or 4 concepts.
2. Type `a`, then `y` to run.
3. No PDFs are downloaded, so it finishes in minutes. The screening lines say "abstract only".

Then ask:

```powershell
uv run chitchat ask -c <run>/pipeline.yaml "Which bias-reduction methods do the papers use?"
uv run chitchat ask -c <run>/pipeline.yaml "Which low-resource languages do the papers study?"
uv run chitchat status -c <run>/pipeline.yaml
```

Answers cite only `[P…]` tags: there are no own documents in this example.

## Minor 2: your documents only

Config: [own-documents/pipeline.yaml](own-documents/pipeline.yaml). No paper search and no screening: the 7 sample documents are read, masked, indexed and questioned.

```powershell
uv run chitchat run -c examples/own-documents/pipeline.yaml --stages ingest,sanitize,export,index
```

| Stage | What you should see |
|---|---|
| ingest | 7 documents read: Markdown, text, email, web page, Word, PDF and Excel |
| sanitize | 83 items masked in own documents: 34 names, 24 dates, 9 places, 9 emails, 7 phone numbers |
| export | 0 papers, 7 own documents |
| index | 0 papers, 7 own documents, about 10 chunks |

Then ask (outputs go to `runs/own-documents-example/`):

```powershell
uv run chitchat ask -c examples/own-documents/pipeline.yaml "What consent approach was agreed with the community in Kakuma?"
uv run chitchat ask -c examples/own-documents/pipeline.yaml "Which calls will never be used to train the chatbot?"
uv run chitchat ask -c examples/own-documents/pipeline.yaml "How can a person withdraw their consent, and until when?"
uv run chitchat ask -c examples/own-documents/pipeline.yaml "Who is the patient who asked for her call to be deleted, and what is her phone number?"
```

The first three cite `[D…]` tags. The last one should give only masked tokens, for example "referred to as [PERSON_4], and her phone number is [PHONE_NUMBER_1] [D0002]". The patient's name and number were removed before indexing.

Expect one quirk: privacy mode may mistake "Kakuma" for a person and send your first question as "…in [PERSON_1]?". The answer is still right, because the documents give the context, and the yellow note tells you it happened. Use `--no-privacy` to compare.

To start again from scratch: `Remove-Item -Recurse runs/own-documents-example`.
