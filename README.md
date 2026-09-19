<a id="readme-top"></a>

<div align="center">
  <img src="docs/assets/logo-wordmark.png" alt="CHITCHAT" width="750">
  <h3>CHITCHAT</h3>
  <p><em>ArCHitectures for Interpretable &amp; Transparent Continuous Humanitarian Alignment in chatbot Technologies</em></p>
  <p>
    <a href="https://fiifidawson.github.io/CHITCHAT/"><strong>Read the documentation »</strong></a>
  </p>
  <p>
    <img alt="License: Apache 2.0" src="https://img.shields.io/badge/license-Apache--2.0-blue">
    <img alt="Python 3.10" src="https://img.shields.io/badge/python-3.10-blue">
    <img alt="Status: experimental" src="https://img.shields.io/badge/status-experimental-orange">
  </p>
</div>

---

## Summary

CHITCHAT is a **reproducible literature-review pipeline** for research on
interpretable, transparent and humanitarian-aligned conversational AI. It turns
a curated vocabulary of research concepts into Boolean search queries, runs them
across four academic repositories, collects and extracts the resulting papers,
and screens them for relevance with LLM assistance — so that a human reviewer
can spend their attention where it counts.

It is a research project of the **Laboratory of Intelligent Global Health &
Humanitarian Response Technologies (LiGHT)** at EPFL, in collaboration with the
**ICRC**. It serves researchers and practitioners who need to know what the
literature says about deploying conversational AI in humanitarian and
global-health settings, and who need to be able to show how they found out.

**Full documentation: <https://fiifidawson.github.io/CHITCHAT/>**

<p align="right">[<a href="#readme-top">back to top</a>]</p>

---

## Research motivation

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

CHITCHAT treats the literature review as **infrastructure** rather than a
one-off exercise. The search is written down as code, so the whole chain —
which terms were used, which sources were queried, which papers were kept and
why — is version-controlled, inspectable and repeatable by anyone.

<p align="right">[<a href="#readme-top">back to top</a>]</p>

---

## Methods

Six stages, each reading a file and writing a file:

| # | Stage | What it does |
|---|---|---|
| 1 | **Boolean combinations** | Expands each concept and its synonyms into quoted `OR` groups for exact-phrase matching |
| 2 | **Unique combinations** | Joins those groups with `AND` across eight research categories |
| 3 | **arXiv search** | Queries arXiv, respecting its rate limits |
| 4 | **Multi-repository search** | Queries OpenAlex, Europe PMC and Google Scholar; deduplicates; downloads and extracts PDFs |
| 5 | **Screening** | Scores each paper against a structured schema and assigns a review priority |
| 6 | **Analysis** | Plots the raw corpus and the screening results |

Because every stage hands a plain data file to the next, any stage can be
re-run, inspected or swapped out on its own.

Three commitments shape the design — **transparency** (nothing is implicit),
**reproducibility** (one changed input, one visible difference) and
**auditability** (you can always see what was excluded and why).

→ [Pipeline reference](https://fiifidawson.github.io/CHITCHAT/pipeline/)

<p align="right">[<a href="#readme-top">back to top</a>]</p>

---

## Installation

Requires **Python 3.10**.

```bash
git clone https://github.com/fiifidawson/CHITCHAT.git
cd CHITCHAT
python3.10 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

> [!NOTE]
> `requirements.txt` lists the pipeline's direct dependencies only; the
> resolver handles the rest. The documentation toolchain is separate and lives
> in the `docs` dependency group in `pyproject.toml` (`uv sync`).
> See the [installation guide](https://fiifidawson.github.io/CHITCHAT/getting-started/installation/)
> for details.

The screening stage needs an OpenAI API key:

```bash
export OPENAI_API_KEY="sk-..."
```

Nothing else in the pipeline requires credentials.

<p align="right">[<a href="#readme-top">back to top</a>]</p>

---

## Quickstart

> [!NOTE]
> A minimal, runnable end-to-end example does not exist yet — every entry point
> currently needs input files. This is the single biggest gap in the project and
> is tracked on the roadmap.

In the meantime, each stage runs on its own, so you can enter the pipeline
wherever you already have the input:

```bash
# Stage 5 — screen an existing corpus
export OPENAI_API_KEY="sk-..."
python legacy/src/screen_papers.py \
    legacy/documentation/prompt/paper_screening_prompt.txt \
    legacy/data/test_papers.json
```

→ [Getting started](https://fiifidawson.github.io/CHITCHAT/getting-started/)

<p align="right">[<a href="#readme-top">back to top</a>]</p>

---

## Limitations and intended use

> [!IMPORTANT]
> **The LLM screening is a decision aid, not a substitute for human systematic
> review.** It narrows a large literature to something a person can read; it
> does not decide what is relevant.

- **The scores are model judgments**, not validated instruments. They have not
  been checked against human annotators, and they change when the model changes.
  Do not report them as findings.
- **The corpus is English-language and skewed by source coverage.** Grey
  literature, NGO and agency reports, and non-English work are largely invisible
  to it — and much humanitarian evidence lives exactly there.
- **Re-running will not reproduce a previous run exactly.** The repositories are
  live and the screening model is non-deterministic. What is reproducible is the
  *method*, not the byte-for-byte result.

→ [Full statement](https://fiifidawson.github.io/CHITCHAT/project/limitations/)

<p align="right">[<a href="#readme-top">back to top</a>]</p>

---

## Main authors

This project is led by the following researchers:

- **Annie Hartley** — EPFL
- **Laura Ferrarello** — EPFL
- **Johan Rochel** — EPFL
- **David Sasu** — EPFL
- **Tim Arni** — EPFL
- **Trevor Brokowski** — EPFL
- **Fiifi Dawson** — EPFL
- **Oriane Peter** — King's College London

<p align="right">[<a href="#readme-top">back to top</a>]</p>

---

## Contributing

Contributions are welcome. Check the
[issues](https://github.com/fiifidawson/CHITCHAT/issues), wait for a maintainer
to assign one, then open a focused pull request that links it.

If you are part of the main project team, reach out to **David**, **Tim** or
**Fiifi** to join the Slack channel.

New to the codebase? [`ARCHITECTURE.md`](ARCHITECTURE.md) is the orientation
map — what each part does, where to make a given change, and the known traps.

→ [Contributing guide](https://fiifidawson.github.io/CHITCHAT/project/contributing/)

<p align="right">[<a href="#readme-top">back to top</a>]</p>

---

## Maintenance status

**Experimental, actively developed.** CHITCHAT is a research pipeline, not a
supported product. There is no release cadence, no deprecation policy and no
support commitment.

<p align="right">[<a href="#readme-top">back to top</a>]</p>

---

## Citation

There is no paper or DOI yet. Cite the repository and the revision you used —
see [Citation](https://fiifidawson.github.io/CHITCHAT/project/citation/) for a
BibTeX entry.

<p align="right">[<a href="#readme-top">back to top</a>]</p>

---

## License

The source code in this repository is licensed under the **Apache License 2.0** —
see [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).

> [!CAUTION]
> The code licence does **not** extend to third-party material this pipeline
> retrieves. Bibliographic metadata, abstracts and extracted document text
> collected from arXiv, OpenAlex, Europe PMC and Google Scholar remain the
> property of their respective rights holders and are not relicensed here. If
> you redistribute outputs of this pipeline, you are responsible for complying
> with the terms of the originating repository and of the underlying
> publications.

→ [Licensing & data rights](https://fiifidawson.github.io/CHITCHAT/project/license/)

<p align="right">[<a href="#readme-top">back to top</a>]</p>
