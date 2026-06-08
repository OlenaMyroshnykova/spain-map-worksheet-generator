# Spain Map Geography Trainer — Project Handoff

**GitHub:** https://github.com/OlenaMyroshnykova/spain-map-worksheet-generator  
**How Claude gets here:** This URL is in the system prompt of every new chat session.

---

## Project overview
Educational geography trainer for a ~10-year-old child (based in Valencia, Spain).  
Inspired by Duolingo, focused on political maps.  
Parent communicates in **Russian** — always respond to parent in Russian.  
Worksheet content language: **Castilian (ES)** and **Valencian (VAL)** — both equal.

**Roadmap:**
1. ✅ Step 1 (current): Printable worksheet generator for Spain
2. Step 2: Interactive browser exercises
3. Step 3: Gamification and progress tracking
4. Future: European countries with flags, world map

## Tech stack
- Plain HTML + JavaScript, single `index.html` to start
- Geographic data in embedded JSON (later: separate `.json` files)
- React planned for future interactive phase

## Principles
1. Start simple and working, then grow
2. Every step produces a usable result
3. All geo data in JSON — easy to add topics and languages

---

## Geographic scope
- **17 Comunidades Autónomas + 2 Ciudades Autónomas** (Ceuta, Melilla)
- **50 provinces**, each with: name (ES + VAL), capital, parent comunidad
- **Priority region:** Comunitat Valenciana — Castelló, València, Alacant

---

## What has been done
*(updated at end of each chat session)*

- [ ] Nothing committed to GitHub yet

---

## Next task
Build `index.html` — self-contained printable worksheet generator:
- Bilingual data (ES / VAL) embedded as JSON
- SVG map of Spain (simplified but accurate)
- Random worksheet generator with exercise types:
  - Labeled reference map
  - Blank map (mapa mudo) — child writes names
  - Color-by-instruction
  - Match province → comunidad
  - Reference table: province / capital / comunidad
- UI controls: language toggle, topic toggle (provincias / comunidades), randomize button
- Print button → clean A4, no UI chrome

---

## Key decisions
- Parent language: **Russian**
- Worksheet language: selectable ES / VAL
- Child age: ~10 years, needs both provinces AND comunidades
- Both provinces and comunidades matter equally
- Start with single self-contained `index.html`

---

## Instructions for Claude

### At session start
1. Read this document (you already have — it's in the system prompt fetch)
2. Summarize to the parent in Russian: what the project is, what was done last time, what's next
3. Ask if they want to continue with "Next task" or change direction

### During session
- Respond to parent in Russian
- Worksheet/UI text: in Spanish and/or Valencian as appropriate
- Commit working code to GitHub when a logical unit is complete

### At session end — MANDATORY
When the conversation reaches ~15 messages OR when a feature is complete, say:

> "Пора открыть новый чат — контекст заполняется. Сейчас обновлю PROJECT.md, чтобы следующий чат знал, где мы остановились."

Then output an updated PROJECT.md with:
- "What has been done" — updated checklist
- "Next task" — what comes next
- Any new decisions made
- Updated changelog

**Do not skip this step.** The updated PROJECT.md is how continuity works across sessions.

---

## Changelog
| Date | What happened |
|------|--------------|
| 2026-06-09 | Project started, PROJECT.md created, worksheet generator planned |
