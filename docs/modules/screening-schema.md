---
title: Screening schema
---

# Screening schema

<span class="chit-status chit-status--wip">Partial</span>

Every paper that passes through [Stage 5](../pipeline/screening.md) produces
one structured record. The schema is defined as Pydantic models in
`legacy/src/screen_papers.py`, which means the model's output is validated
rather than parsed out of prose — the field names below are the contract.

!!! note "Work in progress"

    Field-by-field semantics, scoring rubrics and worked examples are still to
    be written. What follows is the shape of the record.

## `PaperScreening`

The top-level record. Composed of the groups below, plus a priority.

| Field | Type | Meaning |
| --- | --- | --- |
| `publication_quality` | `PublicationQuality` | Venue, peer-review status, citation signals |
| `technical_scope` | `TechnicalScope` | What kind of system or method the paper addresses |
| `ethical_flags` | `EthicalFlags` | Ethical concerns the paper raises or exhibits |
| `humanitarian_principles` | `HumanitarianPrinciples` | Scores against the four core principles |
| `methodology_contributions` | `MethodologyContributions` | What the paper contributes methodologically |
| `ethical_contributions` | `EthicalContributions` | What it contributes to the ethics discussion |
| `priority` | `PriorityLevel` | The triage outcome |

## `HumanitarianPrinciples`

The four principles, each scored `0`–`3`:

| Field | Principle |
| --- | --- |
| `humanity` | Addressing human suffering wherever it is found |
| `impartiality` | Acting on need alone, without discrimination |
| `independence` | Autonomy from political, economic or military objectives |
| `neutrality` | Not taking sides in hostilities or controversies |

!!! danger "These are model judgments"

    The four scores are produced by a language model reading the paper. They
    are **not validated instruments**, they have not been checked against human
    annotators, and they should not be reported as measurements. See
    [Limitations & intended use](../project/limitations.md).

## `PriorityLevel`

A string enum with four values:

| Value | Meaning |
| --- | --- |
| `HIGH PRIORITY` | Read first |
| `MEDIUM PRIORITY` | Read if capacity allows |
| `LOW PRIORITY` | Probably not relevant, but retained |
| `EXCLUDE` | Out of scope |

Exclusion is recorded, not deleted — the point of keeping it is that a human
can see what was excluded and why.

## Output format

One JSON object per line (JSONL), written to
`output/screening_results_<timestamp>.jsonl`. Records are appended as they are
produced, and already-processed papers are skipped on re-run, so an
interrupted run can be resumed.

## Still needed

- [ ] Every field of every sub-model, with its type and permitted values
- [ ] The scoring rubric the prompt actually asks for
- [ ] A worked example record
- [ ] Schema version history, so old result files stay readable
