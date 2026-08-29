# Humani-T — Frontend UI Spec

A simple, modern web app that helps humanitarian AI teams find *ethical tradeoffs* relevant to their
project and see how researchers resolved them. Frontend only.

**The idea:** the user describes their project (Objectives, Environment, Beneficiaries) and Humani-T
returns the most relevant ethical tradeoffs, each shown with its context, the dilemma, the risks, and
recommended ways to resolve it.

**The look:** light, clean, and calm. Soft LiGHT-Lab blue, frosted-glass panels on a luminous
background, generous whitespace. One accent color, restrained type, nothing loud.

---

## Stack
- **Next.js 15** (App Router) + **TypeScript**
- **Tailwind CSS v4** + CSS variables
- **shadcn/ui** for primitives (Textarea, Slider, Accordion, Button, Badge, Sheet, Dialog)
- **lucide-react** icons
- Fonts: **Inter** (UI/body), **Fraunces** (headings) via `next/font`

---

## Color (built on LiGHT-Lab blue `#58A3CF`)

| Token | Value | Use |
|---|---|---|
| `--canvas` | `#EFF6FB` | Page background |
| `--text` | `#122733` | Primary text |
| `--text-muted` | `#5A7789` | Labels, metadata |
| `--primary` | `#58A3CF` | Accent, links, active |
| `--primary-hover` | `#3E82B4` | Buttons, hover |
| `--primary-deep` | `#2C6690` | Wordmark, strong text-on-light |
| `--primary-050` | `#DCEBF5` | Tints, chips |

**Glass:** `background: rgba(255,255,255,0.55)`, `backdrop-blur: 20px`, `border: 1px rgba(255,255,255,0.7)`,
`box-shadow: 0 10px 40px rgba(44,102,144,0.14)` (soft, blue-tinted). Radius `20px` on panels, `12px`
on chips/buttons.

**Signal colors** (small accents only, never big fills): harms/risk = ember `#C2610E`;
recommendations = teal `#0E8A66`. Buttons use `--primary-hover` fill with white text for AA contrast.

**Background:** `--canvas` with 1–2 soft blurred blue blobs (`#8FC2E0`, `#C4DEEF`) behind the content.
Static is fine.

---

## Layout

Two columns on desktop. Left: a sticky glass **search panel** (~340px). Right: **results**.

```
┌───────────────────────────────────────────────────────────┐
│  ◆ Humani-T                        Found 30    [About]     │
├──────────────┬────────────────────────────────────────────┤
│ SEARCH (glass│   ┌─ result card (glass) ──────────────┐    │
│  sticky)     │   │ 01  Tradeoff name                   │    │
│ Objectives   │   │     source paper · authors · year    │    │
│ Environment  │   │     context · dilemma · harms · recs  │    │
│ Beneficiaries│   └──────────────────────────────────────┘    │
│ Matches: 30  │   ┌─ result card ──────────────────────┐    │
│ [ Search ]   │   │ 02 …                                 │    │
│ [ Export ]   │   └──────────────────────────────────────┘    │
└──────────────┴────────────────────────────────────────────┘
```

**Mobile (<1024px):** single column; search panel collapses into a sticky "Refine" bar that opens a
`Sheet`. Cards go full-width.

---

## Data the UI renders (props)

Each card = one tradeoff.

```ts
type Weight = 1 | 2 | 3 | null; // Low / Medium / High relevance

interface Recommendation {
  name: string;
  description: string;
  stages: string[];      // e.g. "Deployment & Local Adaptation"
  finalScore: number;    // sort recommendations desc
}

interface Tradeoff {
  id: string | number;
  name: string;                                  // card headline
  title: string; authors: string; year: string | number; url?: string;
  objective: string; environment: string; beneficiary: string;
  description: string;                           // the dilemma
  harms: string;
  humanity: Weight; neutrality: Weight; independence: Weight; impartiality: Weight;
  recommendations: Recommendation[];
}
```
Render missing values as `N/A` rather than breaking.

---

## Components

**Header** — thin glass bar. Diamond logo + **Humani-T** wordmark (`--primary-deep`). Right: result
count, **About** (Dialog on methodology + the four humanitarian principles), **Export**.

**Search panel** (client) — glass card with:
- Three `Textarea`s: Objectives, Environment, Beneficiaries.
  - Placeholders: *"Biometric registration for aid distribution"*, *"Conflict zone, limited
    connectivity"*, *"Internally displaced persons (IDPs)"*.
- **Matches** slider: 1–100, default **30**.
- **Search** button (primary). Disabled until all three fields are filled.
- **Export CSV** button — appears after results → `humani-t_tradeoffs_top_{N}.csv`.

**Result card** (glass), top to bottom:
1. Faint large rank number + **tradeoff name** (Fraunces).
2. Source line: paper title, then `Authors · Year` caption.
3. **Context** — three chips: Objective / Environment / Beneficiary (muted label + value).
4. **Dilemma / Harms** — two columns (`2fr 1fr`): dilemma prose left; small ember Harms callout right.
   Stacks on mobile.
5. **Principle relevance** — four small labeled meters (Humanity, Neutrality, Independence,
   Impartiality); a short bar filled to the score, colored by severity, labeled High/Med/Low/N-A.
6. **Recommendations** — `Accordion` (top one open). Each: name, description, teal stage chips. Sorted
   by `finalScore` desc.
7. **Read Full Paper** — outline link-button → `url` (new tab); hidden if absent.

Hover: card border brightens toward `--primary` with a slightly stronger shadow.

---

## States
- **Initial** — a short centered explainer with the three example inputs as ghost chips.
- **Loading** — 3–4 skeleton cards.
- **Results** — muted "Found {n} tradeoffs" line above the list.
- **No results** — gentle empty state suggesting broader wording.
- **Missing fields** — inline hint; Search disabled.

---

## Details
- Results fade/slide in with a small stagger. Respect `prefers-reduced-motion`.
- Visible focus rings (`--primary-hover`, 2px) on all interactive elements.
- `tabular-nums` for counts; real `<label>`s on textareas; cards are `<article>`; meters expose values
  via `aria-label`.
- Verify text contrast on glass meets AA (dark text on near-white glass is fine).

---

## Build checklist
- [ ] Next.js 15 + TS + Tailwind v4 + shadcn/ui; color tokens above as CSS variables.
- [ ] Inter + Fraunces via `next/font`; soft blue background blobs.
- [ ] Glass utility (blur + white fill + blue-tinted shadow).
- [ ] `Tradeoff` type; Header, SearchPanel (client), ResultCard, ContextChip, PrincipleMeter,
      RecommendationAccordion.
- [ ] States: initial, loading, results, empty, missing-fields.
- [ ] CSV export; responsive (two-column ≥1024px, Sheet on mobile); a11y + reduced-motion.
