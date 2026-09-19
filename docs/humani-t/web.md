---
title: Web deployment
---

# Humani-T — web deployment

<span class="chit-status chit-status--wip">Version 1 in development</span>

!!! note "Work in progress"

    This page is a placeholder. What follows is the intended shape of the web
    deployment, drawn from the current interface specification; treat it as
    direction, not documentation.

## What it does

A user describes their project — its **objectives**, its **environment** and
its **beneficiaries** — and Humani-T returns the ethical tradeoffs most
relevant to that description. Each tradeoff is shown with its context, the
dilemma it poses, the harms at stake, and the ways researchers have recommended
resolving it, with the source paper attached.

## Intended stack

| Layer | Choice |
| --- | --- |
| Framework | Next.js (App Router) + TypeScript |
| Styling | Tailwind CSS with CSS variables |
| Components | shadcn/ui primitives |
| Icons | lucide-react |

## Look and feel

Light, clean and calm: LiGHT Lab blue, frosted-glass panels on a luminous
background, generous whitespace, one accent colour, restrained type. Signal
colours are used sparingly — a warm tone for harms and risk, a green for
recommendations — and never as large fills.

## Layout

Two columns on desktop: a sticky search panel on the left, results on the
right. Each result is a card carrying the tradeoff name, its source paper and
authors, and the context / dilemma / harms / recommendations breakdown.

## Still needed

- [ ] Hosting target and deployment procedure
- [ ] Whether access is open or authenticated, and on what basis
- [ ] How the corpus is loaded and how often it is refreshed
- [ ] Data residency — what leaves the browser, and where it goes
- [ ] Accessibility commitments
- [ ] How results are ranked, and how that is surfaced to the user
