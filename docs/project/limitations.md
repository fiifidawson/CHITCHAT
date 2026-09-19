---
title: Limitations & intended use
---

# Limitations and intended use

CHITCHAT screens literature about AI systems deployed in health, humanitarian
and policy settings. Work in those domains carries an obligation to be explicit
about what a tool can and cannot support. This page is that statement.

!!! danger "The screening is a decision aid, not a systematic review"

    The pipeline narrows a large body of literature down to something a human
    can read. It does not decide what is relevant, and its output is not a
    systematic review. Every conclusion drawn from this corpus should rest on
    a human having read the papers.

## What the scores are, and are not

The screening stage asks a language model to score each paper against a
structured schema — including the four humanitarian principles of humanity,
impartiality, independence and neutrality.

- **They are model judgments.** They reflect what a language model inferred
  from the text it was given, not a measurement of the paper.
- **They are not validated instruments.** The scoring dimensions were designed
  for this project. They have not been psychometrically validated and have no
  established reliability.
- **They have not been checked against human annotators.** No inter-rater
  agreement has been established between the model's scores and expert
  judgment. Until that is done, agreement is unknown rather than acceptable.
- **They are not stable across models.** Changing the screening model changes
  the scores. The model identifier is part of the experimental record.

Do not report these scores as findings. Use them to decide what to read.

## What the corpus covers, and what it misses

- **English-language only.** The vocabulary, the queries and the screening are
  all in English. Literature published in other languages is absent, and that
  absence is not random — it skews away from exactly the regions much
  humanitarian work concerns.
- **Skewed by source coverage.** The corpus is what arXiv, OpenAlex, Europe PMC
  and Google Scholar return. Work that is not indexed there — grey literature,
  NGO and agency reports, practitioner knowledge — is invisible to it, and a
  great deal of humanitarian evidence lives precisely there.
- **Bounded by the vocabulary.** The search finds what the term list asks for.
  The vocabulary is a deliberate, inspectable artefact, but it encodes choices
  about what "humanitarian alignment", "transparency" and "interpretability"
  mean, and those terms are contested across the fields this draws from.
- **Open access is over-represented.** Full text is extracted where documents
  are openly available, so openly-published work is characterised more richly
  than paywalled work.

## Appropriate use

**Reasonable:**

- Triaging a large literature to decide what to read first
- Making the basis of a review inspectable and repeatable
- Tracking how a body of literature changes between two runs

**Not reasonable:**

- Citing a screening score as evidence about a paper
- Treating the corpus as a complete account of the field
- Using the output to make a decision affecting people's safety, care or
  access to services without expert human review

## Reproducibility, honestly

Re-running the pipeline will not reproduce a previous run byte for byte, and
the reasons are worth stating: the repositories are live and their contents
change; the screening model is non-deterministic and versioned outside this
repository. What *is* reproducible is the method — the vocabulary, the queries
and the criteria are all version-controlled and inspectable, so a reader can
see exactly how a corpus was assembled even where they cannot recreate it
exactly.

## Reporting a concern

If you find a way this output is being relied on that these limits do not
support, that is a problem worth raising. See [Governance](governance.md).
