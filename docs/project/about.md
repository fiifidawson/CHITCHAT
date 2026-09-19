---
title: About
---

# About

**CHITCHAT** — *ArCHitectures for Interpretable & Transparent Continuous Humanitarian
Alignment in chatbot Technologies* — is a research project of the Laboratory of Intelligent
Global Health & Humanitarian Response Technologies at EPFL.

The repository holds the tooling behind the project's literature work: a reproducible
pipeline that turns a curated vocabulary of research concepts into Boolean search queries,
runs those queries across several academic repositories, collects and extracts the resulting
papers, and screens them for relevance.

## Why a pipeline

Systematic reviews at the intersection of AI and humanitarian practice are hard to keep
current. The relevant literature is spread across computer science preprints, open-access
indexes and life-sciences databases, and the search terms themselves are contested — what
counts as "humanitarian alignment" or "transparency" depends on which vocabulary you start
from.

Encoding the search as code rather than as a one-off manual query makes the process
repeatable and auditable: the term list, the Boolean logic derived from it, the repositories
queried, and the screening criteria are all version-controlled artefacts that can be
re-run and inspected.

## Where things are documented

| | |
| --- | --- |
| How the search works, stage by stage | [The pipeline](../pipeline/index.md) |
| Running it yourself | [Getting started](../getting-started/index.md) |
| The reusable parts | [Modules](../modules/index.md) |
| The application built on it | [Humani-T](../humani-t/index.md) |
| What the pipeline cannot tell you | [Limitations & intended use](limitations.md) |

## Contributors

The project is led by researchers at EPFL, with collaborators elsewhere.

| | |
| --- | --- |
| **Annie Hartley** | EPFL |
| **Laura Ferrarello** | EPFL |
| **Johan Rochel** | EPFL |
| **David Sasu** | EPFL |
| **Tim Arni** | EPFL |
| **Trevor Brokowski** | EPFL |
| **Fiifi Dawson** | EPFL |
| **Oriane Peter** | King's College London |

See [Governance](governance.md) for maintainers and contact, and
[Citation](citation.md) for how to cite this work.

## Licence

The source code is released under the **Apache License 2.0**. That licence
covers the code only — it does not extend to the material the pipeline
retrieves. See [Licensing & data rights](license.md) for the full position.
