---
title: Contributing
---

# Contributing

We welcome contributions!❤️ 

If you're part of the main project team, kindly reach out to **David**, **Tim**, or **Fiifi** to join the Slack channel.  

## How to Contribute
1. **Check Issues**  
   - Review the [GitHub Issues](https://github.com/fiifidawson/CHITCHAT/issues) and pick one you'd like to work on.  
   - If you encounter a new problem, [open a new issue](https://github.com/fiifidawson/CHITCHAT/issues/new) with clear details.  

2. **Get Approval**  
   - Wait for project maintainers to approve or assign the issue before starting.  

3. **Make Changes**  
   - Fork the repository.  
   - Create a new branch for your changes.  
   - Implement and test your fix or feature.  

4. **Submit a Pull Request (PR)**  
   - Open a PR describing the problem and your solution.  
   - Link the related issue in your PR description.  

**Notes** 
- PRs should be small, focused, and easy to review.  
- Communication is encouraged—ask questions on Slack if you're unsure.  

## Finding your way around the code

Before your first change, read
[`ARCHITECTURE.md`](https://github.com/fiifidawson/CHITCHAT/blob/main/ARCHITECTURE.md)
at the repository root. It maps the pipeline stage by stage, says which file to
open for a given kind of change — vocabulary, research categories, a new paper
source, the screening schema, a plot — and lists the known traps so you do not
spend an afternoon rediscovering them.

## Documentation

This site is built with [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/).
To work on it:

```bash
uv sync
mkdocs serve
```

The docs toolchain is declared once, in the `docs` dependency group in
`pyproject.toml`. `uv sync` installs it by default. Without `uv`, run
`pip install --group docs` instead (needs pip >= 25.1).

Then open <http://127.0.0.1:8000>. Pages live under `docs/`, and the navigation
is defined in `mkdocs.yml` — a new page has to be added there to appear.

Before opening a pull request that touches the docs:

```bash
mkdocs build --strict
```

`--strict` turns broken internal links and unrecognised navigation entries into
build failures, which is what CI runs. A page that builds locally but not with
`--strict` will fail CI.

### Conventions

- One `#` heading per page; the page title comes from it.
- Mark anything unfinished with a `!!! note "Work in progress"` admonition and
  a `<span class="chit-status chit-status--planned">Placeholder</span>` chip, so
  a reader can tell a gap from an omission.
- Use `!!! danger` for statements about the limits of what the pipeline's output
  can support. Those are the ones that matter most.
