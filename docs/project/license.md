---
title: Licensing & data rights
---

# Licensing and data rights

There are two distinct things in play here and they are licensed differently.
Conflating them is the mistake this page exists to prevent.

## The code

Released under the **Apache License 2.0**. See
[`LICENSE`](https://github.com/fiifidawson/CHITCHAT/blob/main/LICENSE) and
[`NOTICE`](https://github.com/fiifidawson/CHITCHAT/blob/main/NOTICE) in the
repository.

You may use, modify and redistribute the pipeline, including commercially,
subject to the licence's attribution and notice requirements.

## What the pipeline retrieves

!!! danger "The code licence does not cover the data"

    Bibliographic metadata, abstracts and extracted document text collected
    from **arXiv**, **OpenAlex**, **Europe PMC** and **Google Scholar** remain
    the property of their respective rights holders. They are **not**
    relicensed by this project, and Apache-2.0 does not extend to them.

If you redistribute the outputs of this pipeline, you are responsible for
complying with the terms of the originating repository *and* of the underlying
publications. Those terms differ by source and by publisher, and some of them
prohibit redistribution of full text entirely.

| Source | What comes back | Where its terms live |
| --- | --- | --- |
| arXiv | Metadata, abstracts, PDFs | Per-paper licence, set by the submitting author |
| OpenAlex | Metadata, reconstructed abstracts | CC0 for the metadata; abstracts derive from publisher records |
| Europe PMC | Metadata, abstracts, some full text | Varies by article; open-access subset is more permissive |
| Google Scholar | Metadata via scraping | Not an API; subject to Google's terms |

## Practical guidance

- **Sharing a run's outputs internally** is generally unproblematic.
- **Publishing a corpus** containing abstracts or full text is not — check the
  terms for each source and each publication first.
- **Publishing derived fields only** (counts, scores, identifiers, your own
  annotations) is the safer route, and is what we would recommend.

Whether this project publishes its own screening corpus is an open question;
it is tracked on the [Roadmap](roadmap.md).

## Documentation

The prose on this site is part of the repository and is covered by the same
Apache-2.0 licence as the code.
