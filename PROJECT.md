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
├── archive/                    # End-of-session notes (one .md file per session)
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
- [x] `index.html` — printable worksheet generator, all 5 sheet types, ES/VAL, print-ready

### Not done
- [ ] Step 2: Interactive browser exercises (click regions, score tracking)

---

## Next Task: Step 2 — Interactive exercises

The worksheet generator (Step 1) is complete. Step 2 is interactive browser exercises.

### Ideas for Step 2

- Click on a region → type or select its name → get instant feedback
- Score counter + streak
- Timed mode
- Focus mode: only Comunitat Valenciana provinces
- Could reuse the same SVG manipulation approach from index.html

---

## Instructions for Claude

### Session start — required steps

**Step 1: Read this file**

Read `PROJECT.md` directly from the local working directory — no curl or network needed.

**Step 2: Check actual repo state**

Run `git log --oneline` and list the working directory to confirm local file state matches PROJECT.md.

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

**Step 1: Create an archive note**

Create `archive/YYYY-MM-DD-NN.md` (increment NN if multiple sessions on the same day).

Required sections:

- **Accomplished** — completed tasks
- **Next** — what comes next with enough context to resume
- **Key decisions** — technical choices and reasons
- **Session log** — a short human-readable summary of the conversation, written
  in Russian, 5–15 bullet points in plain language: what the parent asked,
  what was discussed, what was chosen and why.

**Step 2: Update PROJECT.md**

- **Status** checklist updated
- **Next Task** updated to reflect what actually comes next
- **Repository Structure** updated if files were added
- **Changelog** entry added (link to archive note)
- Any new decisions recorded

**Do not skip either step.** PROJECT.md + `archive/` are the only memory that survives between sessions.

---

## Changelog

| Date | What happened |
|------|---------------|
| 2026-06-09 | Project started, PROJECT.md created |
| 2026-06-09 | Confirmed repo structure: spain.json + both SVGs ready; index.html is next |
| 2026-06-09 | PROJECT.md rewritten: added data reference, curl instructions, repo structure |
| 2026-06-09 | Removed GitHub curl protocol; added archive/ end-of-session protocol → [archive/2026-06-09-01.md](archive/2026-06-09-01.md) |
| 2026-06-09 | index.html created — all 5 worksheet types, ES/VAL, print-ready → [archive/2026-06-09-02.md](archive/2026-06-09-02.md) |
| 2026-06-09 | Archive protocol extended: Session log section added → [archive/2026-06-09-03.md](archive/2026-06-09-03.md) |
| 2026-06-09 | Dynamic font size for map labels; Canary Islands inset fix attempted and reverted → [archive/2026-06-09-04.md](archive/2026-06-09-04.md) |
