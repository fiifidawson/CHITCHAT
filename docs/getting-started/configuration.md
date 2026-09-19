---
title: Configuration
---

# Configuration

<span class="chit-status chit-status--wip">Partial</span>

!!! note "Work in progress"

    There is no `.env.example` in the repository yet, and the API-key
    requirement currently only surfaces inside `legacy/scripts/screen_papers.sh`.
    This page collects what is known; filling the gaps is tracked on the
    [Roadmap](../project/roadmap.md).

## Environment variables

| Variable | Required by | Notes |
| --- | --- | --- |
| `OPENAI_API_KEY` | [Stage 5 — screening](../pipeline/screening.md) | The only external credential the pipeline needs. Nothing else in the pipeline authenticates. |

```bash
export OPENAI_API_KEY="sk-..."
```

On the EPFL RCP cluster the scripts read the key from a file instead — see
[Running on RCP](../pipeline/running.md#running-on-rcp).

!!! danger "Never commit a key"

    Keys belong in the environment or in a file that `.gitignore` excludes.
    The repository has been scanned and contains no credentials in its history;
    keep it that way.

## Which repositories need credentials

| Source | Credential | Rate limit |
| --- | --- | --- |
| arXiv | none | Be polite; the searcher inserts a delay between queries |
| OpenAlex | none (an email in the user agent gets you the faster pool) | generous |
| Europe PMC | none | generous |
| Google Scholar | none, but it blocks aggressively | scraped, not an API — the fragile one |

## Model pinning

The screening stage currently hardcodes its model in
`legacy/src/screen_papers.py`. Changing models changes the scores, so the
model identifier is part of the experimental record, not an implementation
detail.

## Still needed

- [ ] A `.env.example` committed at the repository root
- [ ] Cost per run, and the hardware assumptions behind it
- [ ] A documented policy for pinning and bumping the screening model
- [ ] Seeds, where any stage is stochastic
