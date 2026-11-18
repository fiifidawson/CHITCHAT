# Use cases to try

Each use case below is something the pipeline is built for, with the commands to run it and what to look for. The sample documents in [examples/my_docs/](../examples/my_docs/) let you try the "own documents" and privacy cases without real data.

*All sample documents are fictional: the organisation, people, phone numbers, emails and IDs are made up.*

## The sample documents

They belong to an invented NGO, the Northbridge Relief Network, which is planning a helpline chatbot trained on call transcripts. Together they tell one story, so questions can draw on several of them.

| File | Format | What it is | What it tests |
|---|---|---|---|
| `field_visit_notes.md` | Markdown | Notes from community sessions in Kakuma | Names, emails, phone numbers, dates and places in own documents |
| `meeting_minutes_llm_data_policy.txt` | Plain text | Working group minutes on LLM training data | Several people, decisions and actions |
| `partner_referral_email.eml` | Email | A doctor's reply about health data | Medical record numbers (MRN), a date of birth, email headers |
| `community_faq_chatbot.html` | Web page | Questions and answers for the community | Little personal data: what is left alone |
| `consent_form_template.docx` | Word | A consent form with a filled-in record | A case ID and staff ID, a Word file |
| `chatbot_pilot_data_policy.pdf` | PDF | The approved data protection policy | No personal data: policy content only |
| `data_inventory.xlsx` | Excel | A table of datasets and their consent status | A spreadsheet |

Use them by copying them into `my_docs/`, the folder the configs read:

| Windows (PowerShell) | macOS (Terminal) |
|---|---|
| `New-Item -ItemType Directory -Force my_docs; Copy-Item examples/my_docs/* my_docs/` | `mkdir -p my_docs && cp examples/my_docs/* my_docs/` |

Or use [examples/own-documents/pipeline.yaml](../examples/own-documents/pipeline.yaml), which reads them where they are.

To rebuild the Word, PDF and Excel files: `uv run python examples/make_samples.py`.

## 1. A quick scan of a new topic

You want a first look at what exists, in minutes.

```bash
uv run chitchat search --mode shallow "How do humanitarian organisations obtain informed consent when collecting data to train LLMs?"
```

Look for:

- One boolean query with 3 or 4 concepts, under 1,500 characters (OpenAlex "ok").
- No PDF downloads: screening reads abstracts, so the whole run takes minutes.
- `prisma.md` in the new run folder, and `dataset.csv` to scan the labels.

## 2. A systematic search, refined with the LLM

You are starting a review and want a careful search.

```bash
uv run chitchat search "How do humanitarian organisations obtain informed consent when collecting data to train LLMs?"
```

Look for:

- 4 clarifying questions first. Try answering `1` (picks a suggestion), a sentence of your own, and Enter (skips).
- 3 to 6 category boxes. Each lists its concepts joined by `AND`, with each concept's synonyms after `or:`.
- Then type `c` and ask for a change, for example "drop generic machine learning terms and add refugee camps". The new draft should reflect it.
- `search/plan.json` in the run folder records every turn.

## 3. Your own documents next to the papers

You have internal notes, emails and policies, and want answers that combine them with the literature.

Copy the samples into `my_docs/` first (see the table above), then:

```bash
uv run chitchat run -c runs/<your-run>/pipeline.yaml --stages ingest,sanitize,export,index
uv run chitchat ask -c runs/<your-run>/pipeline.yaml "What did the working group decide about using helpline transcripts?"
```

Look for:

- `ingest` reads 7 documents (one per file).
- Answers cite `[D0001]`-style tags for your documents, next to `[P0001]` tags for papers.
- Own documents are never screened: they are always indexed.

Questions that need the samples:

- "What consent approach was agreed with the community in Kakuma?" (field notes)
- "Why did the medical coordinator advise against using health calls?" (email)
- "Which datasets are on hold or excluded, and why?" (Excel inventory)
- "What does the policy say about sending data to an external language model API?" (PDF)
- "How do the papers' consent practices compare with our own consent form?" (papers and the Word form)

## 4. Checking what the privacy step removed

You need to show that personal data does not leave your machine.

```bash
uv run chitchat run -c runs/<your-run>/pipeline.yaml --stages ingest,sanitize
```

Then look at `runs/<your-run>/privacy_report.json` and `docs.sanitized.jsonl`. With the samples you should see:

- Names (for example the protection officer and the doctor) replaced by `[PERSON_n]`.
- Emails and phone numbers replaced by `[EMAIL_ADDRESS_n]` and `[PHONE_NUMBER_n]`.
- Dates and places replaced by `[DATE_TIME_n]` and `[LOCATION_n]`: own documents use the broader list.
- The policy PDF and the FAQ almost unchanged: they contain little personal data.

Then ask for personal details, to check nothing leaks into answers:

- "Who wrote the field visit notes, and what is their phone number?" Expect `[PERSON_n]` and `[PHONE_NUMBER_n]`, never the real values.
- "Which patient asked for her call to be deleted, and when was she born?" Expect masked tokens only.

What a test run on the samples found (7 documents, 83 items masked: 34 names, 24 dates, 9 places, 9 emails, 7 phone numbers):

- **Missed: `MRN 448-1207`** in the email. Presidio has no pattern for medical record numbers or case IDs like `KK-2026-00418`.
- **Missed once: "Tomás Herrera"** in the minutes' action list (`- Tomás Herrera: run the re-identification test`). His other mentions were masked. Names at the start of a list item are easy to miss.
- **Emails in `.eml` files** are replaced with `email@email.com` by mmore's email reader, before masking. So every address in an email becomes the same `[EMAIL_ADDRESS_1]`.
- Everything else in the leak list (names, emails and phone numbers in all formats) was masked.

These are good cases to show that masking lowers risk but is not perfect.

## 5. Asking with and without privacy mode

```bash
uv run chitchat ask -c runs/<your-run>/pipeline.yaml "I'm Kwame Asante (kwame.asante@example.org). What do our documents say about opt-out by SMS?"
uv run chitchat ask -c runs/<your-run>/pipeline.yaml --no-privacy "I'm Kwame Asante (kwame.asante@example.org). What do our documents say about opt-out by SMS?"
uv run chitchat ask -c runs/<your-run>/pipeline.yaml --review "What do our documents say about opt-out by SMS?"
```

Look for:

- With privacy: a note that your question was sent as `I'm [PERSON_1] ([EMAIL_ADDRESS_1])…`, and "question: 2 masked" in the privacy line.
- With `--no-privacy`: no note and no privacy line.
- With `--review`: a pause to approve the masked context before anything is sent.

## 6. Changing the screening rules without new LLM calls

You think the labels are too generous and want stricter rules.

1. Edit only the `decision:` rules in `configs/criteria.example.yaml`.
2. Relabel and rebuild the report, with no LLM calls:

```bash
uv run chitchat run -c runs/<your-run>/pipeline.yaml --redecide
uv run chitchat report -c runs/<your-run>/pipeline.yaml
```

Look for a "Relabelled" box with how many labels changed, and new numbers in `prisma.md`.

## 7. The predefined search

You want the original 8-category search from the legacy project.

```bash
uv run chitchat search --predefined
```

Look for: a new run folder with the fixed search, and the OpenAlex warning: all 8 legacy queries are too long for OpenAlex, so only Europe PMC and arXiv return papers.

## 8. Comparing runs and timing

```bash
uv run chitchat status -c runs/<your-run>/pipeline.yaml
```

Look for:

- A "Took" column with each stage's last duration.
- A "Recent runs" table: every `run`, `report` and `search` on this folder, with outcome and total time.
- `runs/<your-run>/logs/` with one log file per run, and `history.jsonl` with the details.
