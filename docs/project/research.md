---
title: Research
---

# The research

<span class="chit-status chit-status--wip">Partial</span>

!!! note "Work in progress"

    The motivation and the category scheme are documented below. The methods
    write-up and the findings are still to come.

## The question

When conversational AI systems are used in humanitarian and global-health
settings, what does it take for them to be *interpretable*, *transparent* and
genuinely *aligned* with humanitarian principles — not once at launch, but
continuously?

## Why it is hard

Chatbots and other language-model systems are increasingly deployed where the
stakes are high and the users are vulnerable: health guidance, crisis response,
humanitarian services. Judging whether such a system is safe and appropriate
means drawing on evidence scattered across very different worlds — machine
learning preprints, medical literature, ethics and policy scholarship,
humanitarian practice.

That evidence is hard to gather and harder to keep current. The vocabulary
itself is contested: what counts as "humanitarian alignment", "transparency" or
"interpretability" depends on which field you start from. A review done by hand
is out of date the moment it is finished, and nobody can check how it was
assembled.

## The response

Treat the literature review as **infrastructure** rather than a one-off
exercise. Write the search down as code, so the whole chain — which terms were
used, which sources were queried, which papers were kept and why — is
version-controlled, inspectable and repeatable by anyone.

[:octicons-arrow-right-24: How that works in practice](../pipeline/index.md)

## Research categories

The vocabulary is organised into eight thematic categories, which are composed
with `AND` to form the search queries. They run from broad foundations through
humanitarian and social concerns to the environmental and infrastructural cost
of the systems being studied.

The category definitions live in
`legacy/src/boolean/unique_boolean_combinations.py` and are documented in
[Stage 2 — Unique combinations](../pipeline/unique-combinations.md), which
lists each one and the concept keys it draws on.

## Still needed

- [ ] Methods write-up — how the vocabulary was constructed and by whom
- [ ] The screening rubric, and the reasoning behind each dimension
- [ ] Results: what the corpus looks like, by source, year and theme
- [ ] Validation of the screening against human annotators
- [ ] Related work and how this review differs from existing ones
