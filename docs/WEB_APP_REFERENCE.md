# CHITCHAT web app: technical reference

This is the reference for building the web version of CHITCHAT. [WEB_APP_BRIEF.md](WEB_APP_BRIEF.md) gives the overview, the data and the security rules; this page gives the parts to build: services, jobs, the agent loop and its data, the decision-brief screens, the model policy, evaluation and the API.

Each part names the module that does the same thing today, so the web app can reuse it or match its behaviour. Paths are under `src/chitchat/`.

## 1. Services

| Service | Does | Network | Today |
|---|---|---|---|
| **Web front end** | Screens, sign-in, live progress | Browser ↔ API only | the terminal UI (`ui.py`) |
| **API** | Projects, search planning, jobs, briefs, questions, exports, permissions | Internal only, behind the gateway | the `chitchat` commands (`cli.py`) |
| **Job workers** | Run stages: discover, ingest, sanitize, screen, export, index, answer, evaluate | Paper sources, PDF hosts, the model server | `stages/`, `agents/`, `evaluate.py` |
| **Privacy worker** | Reads uploads and masks personal data. No LLM | **None** except the job queue and storage | `stages/ingest.py`, `stages/sanitize.py` |
| **Model server** | Serves the open-weight model (OpenAI-compatible `/v1`) | Private network only; no route from the internet | Ollama or vLLM ([MODELS.md](MODELS.md)) |
| **Vector store** | One collection per project | Private network only | Milvus (`stages/index.py`) |
| **Raw store** | Raw papers and uploaded documents | Privacy worker and discover worker only | `runs/<run>/raw/` |
| **Main store** | Masked text, plans, screening, briefs, history | API and workers | the rest of `runs/<run>/` |
| **Queue** | Jobs and their events | Internal | runs in one process today |

Rules that come from the pipeline (details in [WEB_APP_BRIEF.md](WEB_APP_BRIEF.md#security-rules-the-web-app-must-keep)):

- Raw text is read only by the privacy worker. Everything any LLM sees comes from the main store, so it is masked.
- The model server and the vector store are never reachable from the internet.
- Each project has its own vector collection and its own folder of objects. Every API call checks the project's members.

## 2. Jobs and their events

A project is one run folder today. Each job runs stages in this fixed order, and any subset of them:

`queries → discover → ingest → sanitize → screen → export → index → answer`

- **Stage contract:** each stage reads stored objects and writes stored objects. It can be rerun alone. A failure stops the job and keeps finished stages.
- **Reuse:** screening reuses a paper's result when the paper, the criteria hash and the model are unchanged (`screening/store.py`). The answer stage always runs from scratch.
- **History:** one record per job: id, command, start, end, outcome, error, and each stage's start, duration and outcome (`timing.py`, `history.jsonl`).

Events to stream to the browser (Server-Sent Events), one JSON object each:

| Event | Fields | Shown as |
|---|---|---|
| `stage.started` | `stage`, `position`, `total`, `at` | The stage header |
| `stage.progress` | `stage`, `done`, `total`, `item` (e.g. a paper's label) | The progress bar and the latest line |
| `stage.finished` | `stage`, `seconds`, `summary` | A tick and the stage's summary box |
| `agent.step` | the trace event below | A line in the answer panel |
| `job.finished` | `outcome` (`done`, `failed`, `interrupted`), `seconds`, `error` | The job summary |

## 3. Search planning (multi-turn)

`search/session.py::plan_search` is the logic to expose as an API conversation.

1. `POST /projects/{id}/plan` with the question and the mode. The server masks the question (Presidio, no LLM) and returns `question_sent`, so the user sees what was sent.
2. Deep mode: the server returns about 4 clarifying questions, each with suggested answers (`ClarifyingQuestions` in `search/plan.py`). The user answers (each answer is masked too).
3. The server returns a draft (`SearchPlan`: concepts with synonyms, categories combining 2 or more concepts), after fixing rule breaks itself (`plan_problems`, `normalize_plan`, `fit_to_limit`). Notes on every automatic change come with it.
4. The user accepts, or sends a change request in plain words. The server revises the whole plan with the full conversation. Repeat.
5. On accept, the server saves `plan.json` (question, `question_sent`, clarifying answers, every draft and change request, the accepted plan) and the discovery files, and starts the job.

The answer stage later reads `question_sent` and the clarifying answers from `plan.json`, so the final brief answers the question the user started with.

## 4. The agent loop

Code: `agents/` (loop, schemas, prompts, retrieval, checks, render) and `stages/answer.py`. Plain Python with an explicit state; every LLM call returns a schema through structured output (`screening/llm.py::StructuredCaller`).

### Roles

| Role | Kind | Input | Output |
|---|---|---|---|
| **Planner** | LLM | Masked question, clarifying answers, a corpus overview (papers per label, the most relevant titles; document file names are left out) | `Plan` |
| **Retriever** | Code, no LLM | The question and the sub-questions, later the Critic's follow-ups | Passages with their tags, without repeats, up to a character cap |
| **Writer** | LLM | Question, clarifications, plan, passages; on a rewrite also its last draft, the Critic's issues and the failed checks | `BriefDraft` |
| **Checks** | Code, no LLM | The draft and the tags of the retrieved passages | Problems; a citation to an unseen tag is blocking |
| **Critic** | LLM | Question, plan, passages, draft, the checks' problems | `Critique` |

### State and stopping rules

```
plan = Planner(question)
evidence = Retriever([question] + plan.sub_questions)
for round in 1..max_rounds:
    draft = Writer(question, plan, evidence, last critique, last checks, last draft)
    checks = Checks(draft, evidence.tags)
    critique = Critic(question, plan, evidence, draft, checks)
    stop if critique.verdict == accept and not checks.blocking      → "accepted by the Critic"
    stop if round > 1 and no new passages and score <= last score   → "no new evidence and no better score"
    stop if round == max_rounds                                      → "reached the round limit (N)"
    evidence += Retriever(critique.follow_up_queries[:3])
keep the best round: no blocking checks first, then the highest score, then the latest
```

- A Planner failure, or a Writer failure in round 1, fails the stage. A later Writer failure keeps the previous draft; a Critic failure keeps the current draft. The stop reason says which.
- Settings (`answer:` in the config): `max_rounds` 3 (1 to 6), `k_per_query` 6, `max_evidence_chars` 24,000, and an optional `question` for runs without a plan.

### Schemas

`Plan`:

| Field | Type | Notes |
|---|---|---|
| `decision` | string | The decision the researcher faces |
| `options` | string[] | 2 to 4 options, including current practice where it makes sense |
| `criteria` | string[] | Always includes the relevant humanitarian principles |
| `sub_questions` | `{question, purpose}`[] | 4 to 6; `purpose` is `options`, `benefits`, `risks`, `context` or `gaps` |

`Claim` (used inside the brief): `{text, sources: tag[], support: "evidence" | "hypothesis"}`. A tag is `P` or `D` followed by 4 digits.

`BriefDraft` (what the Writer returns):

| Field | Type | Notes |
|---|---|---|
| `bottom_line` | string | 2 or 3 sentences that answer the question |
| `options` | `{name, description, benefits: Claim[], risks: Claim[], evidence_strength}`[] | `evidence_strength`: `strong`, `moderate`, `weak`, `insufficient` |
| `tradeoffs` | `{criterion, assessments: {option, assessment, sources}[]}`[] | One row per criterion, one assessment per option |
| `conflicts` | `{issue, positions: Claim[], conflict_type}`[] | `conflict_type`: `hierarchy` (stronger vs weaker designs), `context` (different settings), `noise` (small, old or unclear studies) |
| `considerations` | `{priority, option, because, sources}`[] | "If this matters most, prefer that option, because …" |
| `gaps` | string[] | What the evidence doesn't cover |

`Critique`:

| Field | Type | Notes |
|---|---|---|
| `verdict` | `accept` or `revise` | |
| `scores` | 6 integers, each 0 to 2 | `coverage`, `groundedness`, `conflict_handling`, `uncertainty`, `humanitarian_awareness`, `specificity`. Out-of-range values are clamped |
| `issues` | `{problem, fix}`[] | |
| `follow_up_queries` | string[] | At most 3 are used |

The stored brief (`answer/brief.json`) is the kept `BriefDraft` plus: `question`, `caveat` (fixed text), `plan`, `rounds`, `kept_round`, `stopped_because`, `verdict`, `scores`, `warnings` (checks still failing), `evidence_passages`, `model`, `written_at`.

The JSON Schemas can be generated from the code, so the front end and the workers never drift apart: `BriefDraft.model_json_schema()`, and the same for the others.

### Trace events

One per step, stored in `answer/trace.jsonl` and streamed as `agent.step`:

| Field | In | Notes |
|---|---|---|
| `round` | all | 0 for the Planner |
| `role` | all | `planner`, `retriever`, `writer`, `checks`, `critic` |
| `status` | all | `ok`, `refused`, `invalid`, `error` |
| `seconds` | LLM steps, retriever | |
| `usage` | LLM steps | `input_tokens`, `output_tokens` |
| `output` | LLM steps | The parsed schema, or null |
| `error` | LLM steps | Short message, or null |
| `queries`, `new_passages`, `total_passages`, `dropped_by_cap` | retriever | |
| `problems` | checks | |

Passages (`answer/evidence.json`): `{tag, chunk_id, query, text}`. The text is masked: it comes from the index.

## 5. Decision-brief screens

The brief is the main output. Build it from `brief.json`, `evidence.json` and the project's sources (tag → title, year, DOI, link, label). The Markdown renderer (`agents/render.py::brief_markdown`) shows the order and wording to follow.

| Part | Shows | Interaction |
|---|---|---|
| **Header** | The question, the bottom line, the model, rounds and why it stopped | "How this was made" opens the trace as a timeline |
| **Option cards** | One per option: description, benefits (green) and risks (red), each with its source chips; an evidence-strength badge | Claims marked `hypothesis` are shown in italics with a "reasoning, not a source" label |
| **Trade-off matrix** | Criteria × options, each cell an assessment with source chips | Sort or highlight by criterion; humanitarian criteria marked |
| **Where the evidence disagrees** | Each conflict with its positions and the kind of disagreement in plain words | |
| **If this matters most** | "Priority → option, because …" rows | The user can pick a priority to highlight its option card |
| **Gaps** | What the evidence doesn't cover | Link to start a new search on a gap |
| **Sources** | Every cited tag: title, year, DOI or link, screening label | |
| **Caveat and warnings** | The fixed caveat; any checks still failing, in amber | Always visible, never collapsible |

Citations: every source chip opens a side panel with the cited passage(s) from `evidence.json`, the paper's title and link, and its screening evidence. A chip whose tag isn't in the evidence must never appear: the checks forbid it, and the UI should treat one as an error.

Accessibility: evidence strength and benefit or risk are shown with words or icons, not colour alone.

## 6. Model policy

- **Open-weight models only** in production, served by the organisation: Ollama for small deployments, vLLM on a GPU server for teams. Default `qwen3.5:9b`; larger options in [MODELS.md](MODELS.md).
- **A hosted provider** only when it doesn't train on prompts, keeps none (zero retention), and is under a contract that suits the organisation. Masked text only.
- **One model per deployment**, set by an admin; not per user. The judge for evaluation may differ.
- **Record the model** in every output: screening records, briefs, evaluation summaries.
- **Check the model server** at job start (`screening/llm.py::check_llm_reachable`) and fail the job with a clear message if it is down or the model is missing.
- **Context length:** run the model with at least 16k tokens of context; screening caps each paper's text (`screening.max_chars`) to fit.
- **Structured output:** `json_schema` by default; `json_mode` (with the schema in the prompt) or `function_calling` as fallbacks per model (`llm.structured_output`).

## 7. Evaluation

Code: `evaluate.py`. An admin feature to compare CHITCHAT with other systems on a question set.

- **Systems per question:** a single-pass baseline (one search of 10 passages, one Writer call with the same prompt), the full loop, and any imported system (an answer file per question).
- **Judge:** blind and pairwise. CHITCHAT against each other system, in random order (seeded), with no system names. Six metrics, 1 to 5: coverage, groundedness, specificity, trade-offs, humanitarian awareness, usefulness; plus a winner and a reason. Then unblinded.
- **Outputs:** every answer, every judgement with its display order, and a summary: means per metric, deltas, wins, ties and losses.
- **Screens:** upload a question set and other systems' answers; a results table per system pair; each judgement with both answers side by side.
- **Fairness:** a judge from a different model family than the Writer; the same index and model for every CHITCHAT variant; record the seed.

## 8. API

A first set of endpoints. All require sign-in; `{id}` is a project the caller is a member of.

| Method and path | Does | Today |
|---|---|---|
| `POST /projects` | New project (name, mode, template) | `chitchat search` (run folder) |
| `POST /projects/{id}/plan` | Start planning: question, mode → masked question, clarifying questions or a draft | `plan_search` |
| `POST /projects/{id}/plan/answers` | Clarifying answers → draft | `plan_search` |
| `POST /projects/{id}/plan/changes` | A change request → new draft | `add_feedback` |
| `POST /projects/{id}/plan/accept` | Save the plan and start the job | `save_plan`, `write_run_config` |
| `POST /projects/{id}/documents` | Upload own documents (checked, scanned, to the raw store) | `my_docs/` |
| `POST /projects/{id}/jobs` | Run stages (`stages`, or `redecide`) | `chitchat run` |
| `GET /projects/{id}/jobs/{job}/events` | Live events (SSE) | the terminal output |
| `POST /projects/{id}/jobs/{job}/cancel` | Stop a job, keep finished stages | Ctrl+C |
| `GET /projects/{id}/status` | Stages, durations, recent jobs | `chitchat status` |
| `GET /projects/{id}/papers` | Screening results with evidence, filters | `dataset.jsonl` |
| `PUT /projects/{id}/rules` | Edit the label rules, then relabel with no LLM calls | `--redecide` |
| `GET /projects/{id}/exports/{name}` | `dataset.csv`, `dataset.jsonl`, `prisma.md`, `brief.md` | `export`, `answer` |
| `GET /projects/{id}/brief` | The decision brief (`brief.json`) | `answer` |
| `GET /projects/{id}/brief/evidence/{tag}` | The passages behind a citation | `evidence.json` |
| `GET /projects/{id}/brief/trace` | The agent steps | `trace.jsonl` |
| `POST /projects/{id}/questions` | A follow-up question → answer with sources and privacy summary | `chitchat ask` |
| `POST /admin/evaluations` | Run an evaluation on a project | `chitchat evaluate` |
| `GET /admin/evaluations/{eval}` | Its answers, judgements and summary | `eval/<run id>/` |
| `DELETE /projects/{id}` | Delete everything: raw text, index, logs | delete the run folder |

Errors follow one shape: `{error: {code, message}}`, where `message` is plain language (the pipeline's messages are written for that). Never return raw text, keys or stack traces.

## 9. What to keep in the first version

- The fixed stage order, stage reuse and the job history.
- Masking before any LLM, in an isolated worker.
- The agent loop as it is: four roles, structured outputs, checks by code, at most 3 rounds.
- The brief screen with source chips that open the passages.
- One open model per deployment, checked at job start.

Later: user-edited screening questions, several models per deployment, an evidence graph across briefs (DeepEvidence's idea), and evaluation with human raters next to the judge model.
