---
title: Local deployment
---

# Humani-T — local deployment

<span class="chit-status chit-status--wip">Version 1 in development</span>

!!! note "Work in progress"

    This page is a placeholder. The local deployment is the less-specified of
    the two forms; this page exists so its constraints can be captured as they
    are decided rather than reconstructed afterwards.

## Why a local form exists

The [web deployment](web.md) assumes connectivity and a hosted service.
Neither assumption holds everywhere Humani-T is meant to be useful. Teams
working in constrained environments, on sensitive projects, or without
dependable connectivity need the same tool without the network.

The local deployment runs on one machine against a local copy of the screened
corpus, and should work with the network unplugged.

## Design constraints

| Constraint | Why it matters |
| --- | --- |
| **Works offline** | The environments this is built for cannot assume connectivity |
| **Data stays local** | Project descriptions may be sensitive; nothing should leave the machine |
| **Corpus is a file** | A snapshot you can copy onto a laptop, carry, and verify |
| **Same answers as the web form** | The two deployments must not diverge in what they recommend |

## Still needed

- [ ] Packaging and install procedure per platform
- [ ] How a corpus snapshot is obtained, verified and updated
- [ ] Minimum hardware
- [ ] An explicit statement of what, if anything, touches the network
- [ ] How to confirm the local and web deployments agree
