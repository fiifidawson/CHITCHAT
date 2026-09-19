---
title: Getting Started
---

# Getting Started

There are three ways into CHITCHAT, depending on what you came for.

<div class="grid cards" markdown>

-   :material-book-open-page-variant:{ .lg .middle } __Read the method__

    ---

    Understand how the review was assembled without running anything — the
    vocabulary, the query logic, the sources and the screening criteria.

    [:octicons-arrow-right-24: The pipeline](../pipeline/index.md)

-   :material-console:{ .lg .middle } __Run the pipeline__

    ---

    Reproduce the search, or re-run it with your own vocabulary to produce an
    updated review.

    [:octicons-arrow-right-24: Installation](installation.md)

-   :material-puzzle:{ .lg .middle } __Build on the modules__

    ---

    Lift paper discovery or the analytics layer out of CHITCHAT and use them
    in your own project.

    [:octicons-arrow-right-24: Module specs](../modules/index.md)

</div>

## The short version

```bash
git clone https://github.com/fiifidawson/CHITCHAT.git
cd CHITCHAT
python3.10 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY="..."        # screening stage only
```

Then pick a stage from the [pipeline reference](../pipeline/index.md). Each
stage reads a file and writes a file, so you can start anywhere you already
have the input for.

!!! warning "Read this first"

    The screening stage uses an LLM to score papers for relevance. Those scores
    are a **decision aid, not a substitute for human systematic review**. See
    [Limitations & intended use](../project/limitations.md) before relying on
    any output.

## In this section

| Page | What it covers |
| --- | --- |
| [Installation](installation.md) | Python version, virtual environment, dependency caveats |
| [Quickstart](quickstart.md) | The shortest path to a first result |
| [Configuration](configuration.md) | API keys, environment variables, model pinning |
| [Project layout](project-layout.md) | What lives where in the repository |
