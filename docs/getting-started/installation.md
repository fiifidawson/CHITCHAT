---
title: Installation
---

# Installation

CHITCHAT runs on **Python 3.10**. Every stage is a plain script reading and
writing JSON, so there is nothing to compile and nothing to install as a
package — you clone the repository, create a virtual environment, and run the
stage you need.

## Prerequisites

| | |
| --- | --- |
| **Python** | 3.10 (the pipeline is developed and run against this version) |
| **OpenAI API key** | Required for [Stage 5 — screening](../pipeline/screening.md) only. See [Configuration](configuration.md). |
| **Disk space** | The discovery stages download PDFs; budget generously if you widen the vocabulary. |

## Create a virtual environment

=== "Linux / macOS"

    ```bash
    # On Debian/Ubuntu, install the interpreter first:
    sudo apt update
    sudo apt install python3.10 python3.10-venv

    python3.10 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```

    Leave the environment with `deactivate`.

=== "Windows"

    ```cmd
    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt
    ```

    Leave the environment with `deactivate`.

!!! note "What `requirements.txt` contains"

    `requirements.txt` lists the pipeline's **direct** dependencies only, with
    a comment naming the stage each one serves. Transitive packages are left to
    the resolver. It replaced a raw `pip freeze` that did not install a working
    environment — that version shadowed the stdlib with `pathlib==1.0.1`,
    included the `bs4==0.0.2` dummy, pinned an unrelated neuroimaging stack,
    and omitted six packages the code imports.

    Two entries are load-bearing and should not be "tidied away":

    - **PyMuPDF** is what `import fitz` resolves to. A different, unrelated
      package named `fitz` exists on PyPI; installing it breaks the scraper.
    - **`bibtexparser<2`** constrains a transitive dependency. `scholarly`
      requests it unpinned but imports `bibtexparser.bibdatabase`, which
      version 2.x removed, so an unconstrained install makes
      `import scholarly` fail.

    The documentation toolchain is separate — it lives in the `docs`
    dependency group in `pyproject.toml`.

    Repairing the dependency set is tracked on the [Roadmap](../project/roadmap.md).
    Until then, expect to install the stage-specific packages by hand.

## Verify

```bash
python --version        # should report 3.10.x
python -c "import openai, requests; print('core imports OK')"
```

## Next

- [Configuration](configuration.md) — API keys and environment variables.
- [Quickstart](quickstart.md) — the shortest path to a first result.
- [Project layout](project-layout.md) — where everything lives on disk.
