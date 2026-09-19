---
template: home.html
description: A reproducible, auditable literature-review pipeline for humanitarian AI alignment research.
hide:
  - navigation
  - toc
---

## Why it exists

Chatbots and other language-model systems are increasingly deployed where the
stakes are high and the users are vulnerable: health guidance, crisis response,
humanitarian services. Judging whether such a system is safe and appropriate
means drawing on evidence scattered across machine-learning preprints, medical
literature, ethics scholarship and humanitarian practice — evidence that is hard
to gather, harder to keep current, and assembled in ways nobody else can check.

CHITCHAT treats the literature review as **infrastructure** rather than a
one-off exercise. Which terms were used, which sources were queried, which
papers were kept and why — all of it is version-controlled and inspectable.

## How it works

<div class="chit-diagram" markdown>
<svg viewBox="0 0 900 190" role="img" aria-label="Six pipeline stages: vocabulary, Boolean groups, category queries, multi-repository search, text extraction, screening, then analysis and Humani-T." xmlns="http://www.w3.org/2000/svg">
  <defs>
    <marker id="chit-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto">
      <path class="flow-head" d="M0 0 L8 4 L0 8 Z"/>
    </marker>
  </defs>

  <g class="flow" marker-end="url(#chit-arrow)">
    <path d="M132 62 L146 62"/>
    <path d="M268 62 L282 62"/>
    <path d="M404 62 L418 62"/>
    <path d="M560 62 L574 62"/>
    <path d="M696 62 L710 62"/>
    <path d="M832 62 L846 62"/>
    <path d="M771 92 L771 124 L846 124"/>
  </g>

  <g>
    <rect class="node" x="10" y="38" width="122" height="48" rx="7"/>
    <text class="label" x="71" y="60" text-anchor="middle">Vocabulary</text>
    <text class="sublabel" x="71" y="75" text-anchor="middle">terms + synonyms</text>
  </g>
  <g>
    <rect class="node" x="146" y="38" width="122" height="48" rx="7"/>
    <text class="label" x="207" y="60" text-anchor="middle">Boolean groups</text>
    <text class="sublabel" x="207" y="75" text-anchor="middle">quoted OR sets</text>
  </g>
  <g>
    <rect class="node" x="282" y="38" width="122" height="48" rx="7"/>
    <text class="label" x="343" y="60" text-anchor="middle">Category queries</text>
    <text class="sublabel" x="343" y="75" text-anchor="middle">8 categories, AND</text>
  </g>
  <g>
    <rect class="node" x="418" y="38" width="142" height="48" rx="7"/>
    <text class="label" x="489" y="60" text-anchor="middle">Repository search</text>
    <text class="sublabel" x="489" y="75" text-anchor="middle">arXiv · OpenAlex · EPMC · Scholar</text>
  </g>
  <g>
    <rect class="node" x="574" y="38" width="122" height="48" rx="7"/>
    <text class="label" x="635" y="60" text-anchor="middle">Extraction</text>
    <text class="sublabel" x="635" y="75" text-anchor="middle">PDFs + full text</text>
  </g>
  <g>
    <rect class="node node--accent" x="710" y="38" width="122" height="54" rx="7"/>
    <text class="label label--invert" x="771" y="61" text-anchor="middle">Screening</text>
    <text class="label label--invert" x="771" y="78" text-anchor="middle" opacity="0.72">scored + ranked</text>
  </g>
  <g>
    <rect class="node" x="846" y="38" width="44" height="48" rx="7"/>
    <text class="label" x="868" y="66" text-anchor="middle">Plots</text>
  </g>
  <g>
    <rect class="node" x="846" y="100" width="44" height="48" rx="7"/>
    <text class="label" x="868" y="123" text-anchor="middle">Humani</text>
    <text class="label" x="868" y="134" text-anchor="middle">-T</text>
  </g>

  <text class="sublabel" x="10" y="178">Every stage reads a file and writes a file — so any stage can be re-run, inspected or replaced on its own.</text>
</svg>
</div>

## Start here

<div class="grid cards" markdown>

-   :material-rocket-launch:{ .lg .middle } __Get started__

    ---

    Install the pipeline, configure your credentials, and find the shortest
    path to a first result.

    [:octicons-arrow-right-24: Getting started](getting-started/index.md)

-   :material-pipe:{ .lg .middle } __The pipeline__

    ---

    Six stages, from a curated vocabulary through multi-repository search to
    LLM-assisted screening — each with its data contracts documented.

    [:octicons-arrow-right-24: Pipeline reference](pipeline/index.md)

-   :material-package-variant:{ .lg .middle } __Modules__

    ---

    Paper Discovery and LitLens are designed to be lifted out and reused on
    their own, independently of CHITCHAT.

    [:octicons-arrow-right-24: Module specs](modules/index.md)

-   :material-application-brackets:{ .lg .middle } __Humani-T__

    ---

    The application built on the CHITCHAT corpus, in two deployments — one
    web-served, one local-served.
    <span class="chit-status chit-status--wip">v1 in development</span>

    [:octicons-arrow-right-24: Humani-T](humani-t/index.md)

-   :material-scale-balance:{ .lg .middle } __Limitations__

    ---

    LLM-assisted screening is a decision aid, not a substitute for human
    systematic review. Read this before relying on any output.

    [:octicons-arrow-right-24: Limitations & intended use](project/limitations.md)

-   :material-account-group:{ .lg .middle } __The project__

    ---

    Who is behind CHITCHAT, how to contribute, how to cite it, and what is
    licensed to whom.

    [:octicons-arrow-right-24: About](project/about.md)

</div>

## Three commitments

<div class="grid cards" markdown>

-   :material-eye-outline:{ .lg .middle } __Transparency__

    ---

    Nothing in the process is implicit. The term list, the query logic, the
    sources and the screening criteria are all artefacts you can read.

-   :material-repeat:{ .lg .middle } __Reproducibility__

    ---

    Someone else, starting from the same repository, gets the same result — and
    can change one input to see what it changes.

-   :material-gavel:{ .lg .middle } __Auditability__

    ---

    Automated screening narrows the field; it does not make the final call.
    A human can always see what was excluded, and why.

</div>

!!! danger "Status: experimental, actively developed"

    CHITCHAT is a research pipeline, not a supported product. LLM-assisted
    screening is a **decision aid, not a substitute for human systematic
    review**, and the scores it produces are model judgments rather than
    validated measurements. Please read
    [Limitations & intended use](project/limitations.md) before relying on any
    output.
