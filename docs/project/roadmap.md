---
title: Roadmap
---

# Roadmap

This project audited itself against the
[LiGHT GitHub Repository Checklist](https://lighters-playground.github.io/LiGHT-doc/checklist/)
before release. The audit is blunt about what is missing, and this page tracks
the work that came out of it. The full audit lives in the repository at
`legacy/documentation/OSS-Readiness-Plan.md`.

!!! note "Work in progress"

    Status below reflects the documentation revamp. The code-side items have
    not been re-audited since.

## Where things stand

| Area | Status |
| --- | --- |
| Licence and third-party content statement | :material-check: Done |
| Documentation site and structure | :material-progress-check: In progress |
| README | :material-progress-check: In progress |
| Limitations and intended use | :material-check: Written |
| Dependency set (`requirements.txt`) | :material-close: Broken — see [Installation](../getting-started/installation.md) |
| Quickstart / minimal runnable example | :material-close: Not started |
| Reproducibility statement | :material-progress-check: Stated in [Limitations](limitations.md), needs detail |
| Tests | :material-close: None |
| Citation metadata | :material-close: Not started |
| Governance files | :material-progress-check: [Governance](governance.md) written; `SECURITY.md`, code of conduct outstanding |
| Versioning and releases | :material-close: No tags |

## Documentation

- [x] Replace the MkDocs boilerplate home page
- [x] Split the single 2,600-line technical report into per-stage pages
- [x] Write limitations and intended use
- [x] Give the site a navigable structure and a real theme
- [ ] Fill the quickstart
- [ ] Document the analysis stage
- [ ] Complete the screening schema reference
- [ ] Fill the Humani-T pages as v1 lands

## Code and packaging

- [x] Repair `requirements.txt` — replaced the raw `pip freeze` with a
      curated list of direct dependencies
- [ ] Remove hardcoded personal cluster paths from the shell scripts
- [ ] Stop the scripts installing dependencies at runtime
- [ ] Extract `paper_discovery` and `litlens` per their [design specs](../modules/index.md)
- [ ] Add a test suite, starting with the pure functions in `legacy/src/boolean/`

## Data and release

- [ ] Decide what happens to committed run artefacts — keep a small fixture,
      move full outputs to a release or archive
- [ ] `CITATION.cff` and a DOI
- [ ] `CHANGELOG.md` and a first tagged release
- [ ] Resolve whether the screening corpus itself is published, or only the
      pipeline that produces it — this is the one open question that changes
      what else is needed
