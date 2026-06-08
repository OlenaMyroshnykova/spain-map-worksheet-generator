# Spain Map Geography Trainer — Project Handoff

**Repository:** https://github.com/OlenaMyroshnykova/spain-map-worksheet-generator

> This file is read by Claude at the start of every chat session.
> Keep it up to date. It is the single source of truth for project state.

---

## Overview

Educational geography trainer for a child (~10 years old, based in Valencia, Spain).  
Inspired by Duolingo. Focused on political maps.

| | |
|---|---|
| **Target user** | Child learning geography in Castilian and Valencian |
| **Parent language** | Russian — Claude always responds to parent in Russian |
| **Worksheet languages** | Castilian (ES) and Valencian (VAL) — equal priority |
| **Priority region** | Comunitat Valenciana (Castelló, València, Alacant) |

---

## Roadmap

| Step | Status | Description |
|------|--------|-------------|
| 1 | 🔄 In progress | Printable worksheet generator |
| 2 | ⏳ Planned | Interactive browser exercises |
| 3 | ⏳ Planned | Gamification + progress tracking |
| ∞ | 💭 Future | European countries, world map |

---

## Tech Stack

- Plain HTML + vanilla JavaScript — no build step, no framework
- Single `index.html` — self-contained, opens in any browser
- Geographic data in `data/spain.json` — bilingual, easy to extend
- SVG maps in `maps/` — pre-generated, manipulated by JS at runtime
- React considered for Step 3+

---

## Principles

1. Start simple and working, then grow
2. Every step produces a usable result
3. Geographic data lives in JSON — adding new topics/languages = adding data, not code

---

## Repository Structure

```
spain-map-worksheet-generator/
│
├── data/
│   └── spain.json              # All geographic data, bilingual ES + VAL
│
├── maps/
│   ├── provinces.svg           # 52 provinces (pre-generated, do not edit manually)
│   └── communities.svg         # 19 comunidades (pre-generated, do not edit manually)
│
├── scripts/
│   └── generate_svg.py         # Generates both SVGs from public GeoJSON — already run
│
├── requirements.txt            # Python deps for generate_svg.py
├── README.md
├── PROJECT.md                  # ← you are here
└── index.html                  # ← NOT YET CREATED (next task)
```

---

## Data Reference

### `data/spain.json`

```jsonc
{
  "autonomousCommunities": [
    {
      "id": "valencianCommunity",   // camelCase, matches SVG data-community-id
      "code": "19",                  // 2-digit string, matches SVG data-community-code
      "names": {
        "castilian": "Comunidad Valenciana",
        "valencian": "Comunitat Valenciana"
      },
      "capital": {
        "castilian": "Valencia",
        "valencian": "València"
      },
      "mapColor": "#7DCEA0"
    }
    // ...18 more
  ],
  "provinces": [
    {
      "id": "valencia",             // camelCase, matches SVG data-province-id
      "code": "46",
      "communityCode": "19",        // links to autonomousCommunity.code
      "names": {
        "castilian": "Valencia",
        "valencian": "València"
      },
      "capital": {
        "castilian": "Valencia",
        "valencian": "València"
      }
    }
    // ...51 more
  ]
}
```

**Counts:** 19 comunidades · 52 provinces

### `maps/provinces.svg`

Each province is an SVG `<path>` with:
```html
<path
  id="province-46"
  data-province-id="valencia"      <!-- matches provinces[].id in spain.json -->
  data-community-code="19"         <!-- matches autonomousCommunities[].code -->
  fill="#7DCEA0"                   <!-- community colour -->
  d="..." />
```

### `maps/communities.svg`

Each comunidad is an SVG `<path>` with:
```html
<path
  id="community-19"
  data-community-id="valencianCommunity"   <!-- matches autonomousCommunities[].id -->
  data-community-code="19"
  fill="#7DCEA0"
  d="..." />
```

---

## Status

### Done
- [x] `data/spain.json` — complete, all 52 provinces + 19 comunidades, bilingual
- [x] `maps/provinces.svg` — 52 provinces, correct IDs and community colours
- [x] `maps/communities.svg` — 19 comunidades, dissolved from province geometry
- [x] `scripts/generate_svg.py` — working, no need to re-run unless data changes

### Not done
- [ ] `index.html` — printable worksheet generator (see Next Task below)

---

## Next Task: `index.html`

A single self-contained HTML file. No build step. Opens in browser, prints to A4.

### Data loading
- Fetch `spain.json` and both SVGs from GitHub raw URLs using `fetch()`
- Embed SVG inline into DOM (not `<img>`) — required for JS to manipulate paths

### UI controls (hidden on print)
| Control | Options |
|---------|---------|
| Language | Castilian / Valencian |
| Topic | Provincias / Comunidades |
| Worksheet type | see below |
| Randomize | regenerates random subsets |
| Print | triggers `window.print()` |

### Worksheet types
| # | Name | Description |
|---|------|-------------|
| 1 | Mapa de referencia | Coloured map, all names labeled |
| 2 | Mapa mudo | Outline map only, child writes names |
| 3 | Colorea el mapa | Blank map + colour legend (random subset of regions) |
| 4 | Tabla de referencia | Table: province / capital / comunidad |

### Print layout
- A4 portrait, `@media print` hides all UI chrome
- Style: clean, child-friendly, edufichas.com aesthetic (dotted borders, clear fonts)
- No external dependencies at print time

---

## Instructions for Claude

### Session start — required steps

**Step 1: Read this file**

Use `bash_tool` with `curl`. Do NOT use `web_fetch` for raw.githubusercontent.com
URLs — it requires a prior search result and will fail.

```bash
curl https://raw.githubusercontent.com/OlenaMyroshnykova/spain-map-worksheet-generator/main/PROJECT.md
```

**Step 2: Check actual repo state**

`web_fetch` works fine for the GitHub HTML page:
```
https://github.com/OlenaMyroshnykova/spain-map-worksheet-generator
```

This shows real file list and latest commits — use it to verify PROJECT.md is current.

**Step 3: Greet parent in Russian**

Summarise: what was done last session, what is next, ask if they want to continue
or change direction.

### During session

- Respond to parent in **Russian** at all times
- Worksheet and UI text: Spanish and/or Valencian as appropriate
- Read any repo file via curl in bash_tool:
  ```bash
  curl https://raw.githubusercontent.com/OlenaMyroshnykova/spain-map-worksheet-generator/main/data/spain.json
  curl https://raw.githubusercontent.com/OlenaMyroshnykova/spain-map-worksheet-generator/main/maps/provinces.svg
  ```
- Commit working code to GitHub when a logical unit is complete

### Session end — mandatory

When the conversation reaches ~15 messages OR a feature is complete:

> "Пора открыть новый чат — контекст заполняется. Сейчас обновлю PROJECT.md."

Then produce an updated PROJECT.md with:
- **Status** checklist updated
- **Next Task** updated to reflect what actually comes next
- **Repository Structure** updated if files were added
- **Changelog** entry added
- Any new decisions recorded

**Do not skip this step.** PROJECT.md is the only memory that survives between sessions.

---

## Changelog

| Date | What happened |
|------|---------------|
| 2026-06-09 | Project started, PROJECT.md created |
| 2026-06-09 | Confirmed repo structure: spain.json + both SVGs ready; index.html is next |
| 2026-06-09 | PROJECT.md rewritten: added data reference, curl instructions, repo structure |
