---
title: Citation
---

# Citing CHITCHAT

<span class="chit-status chit-status--planned">Placeholder</span>

!!! note "Work in progress"

    There is no published paper, DOI or `CITATION.cff` for this project yet.
    Until there is, cite the repository directly, and please state which
    revision you used — the corpus a run produces depends on when it ran.

## For now

Cite the software and the revision:

```bibtex
@software{chitchat,
  title  = {{CHITCHAT}: {ArCHitectures} for {Interpretable} and {Transparent}
            {Continuous} {Humanitarian} {Alignment} in chatbot {Technologies}},
  author = {Hartley, Annie and Ferrarello, Laura and Rochel, Johan and
            Sasu, David and Arni, Tim and Brokowski, Trevor and
            Dawson, Fiifi and Peter, Oriane},
  url    = {https://github.com/fiifidawson/CHITCHAT},
  note   = {Laboratory of Intelligent Global Health and Humanitarian Response
            Technologies, EPFL}
}
```

Add the commit hash and the date of the run you are describing.

!!! danger "Cite the papers, not the scores"

    If you are reporting what the literature says, cite the underlying papers.
    The screening scores this pipeline produces are model judgments and are not
    citable findings — see [Limitations & intended use](limitations.md).

## Still needed

- [ ] A `CITATION.cff` at the repository root, so GitHub renders a citation box
- [ ] ORCIDs for each author
- [ ] A DOI, via a tagged release archived to Zenodo
- [ ] The preferred citation once a paper is published
- [ ] Guidance on citing the corpus itself, if it is ever published separately
