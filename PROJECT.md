# Spain Map Geography Trainer — Project Handoff

## GitHub
https://github.com/OlenaMyroshnykova/spain-map-worksheet-generator

## What this project is
An educational geography trainer for a ~10-year-old child, inspired by Duolingo but for political maps. Step 1 is **printable worksheet generator** for Spain. Future: interactive web app, European countries, world map.

**User:** Child learning in **Castilian (Spanish) and Valencian**, based in Valencia region of Spain.

## Tech stack
- Plain HTML + JavaScript (no framework yet)
- Geographic data stored in **JSON files** (easy to extend)
- React planned for future interactive phase

## Principles
1. Start simple and working, then grow
2. Every step produces a usable result
3. All geo data in JSON — easy to add topics and languages

## Languages
- **Castilian** (castellano / español)
- **Valencian** (valencià) — co-equal, not secondary

## Current stage: Step 1 — Printable Worksheets

### What has been done
- [ ] Nothing committed to GitHub yet — project is being set up

### What is being built RIGHT NOW
A self-contained `index.html` worksheet generator that:
- Contains Spain geographic data (provinces + autonomous communities) in embedded JSON, bilingual ES/VAL
- Draws a simplified SVG map of Spain
- Generates **random** printable worksheets
- Exercise types (inspired by edufichas.com PDF style):
  - Labeled reference map (comunidades / provinces with names)
  - Blank map — write the names (mapa mudo)
  - Color-by-instruction — color specified regions
  - Match province → comunidad
  - Reference table: province / capital / comunidad
- Language toggle: Castellano / Valencià
- Topic toggle: Provincias / Comunidades Autónomas
- Print button → clean A4 output, no UI chrome

### Key geographic data to include
**17 Comunidades Autónomas + 2 Ciudades Autónomas**, all 50 provinces, with:
- Name in Castilian
- Name in Valencian
- Capital city
- Which comunidad each province belongs to

### Child's home region
**Comunitat Valenciana** — 3 provinces: Castelló, València, Alacant. Emphasize this region.

---

## Instructions for Claude in a new chat

You are continuing development of this educational geography trainer. The conversation must be in **Russian** (the parent communicates in Russian). The child uses Spanish and Valencian.

### How to start
1. Read this document fully
2. Check the GitHub repo for what's actually been committed: https://github.com/OlenaMyroshnykova/spain-map-worksheet-generator
3. Ask the parent what to work on next, or continue from "What is being built RIGHT NOW"

### How to end a session
Before the conversation gets too long (context window filling up), **proactively suggest** starting a new chat. Say something like:

> "Скоро стоит начать новый чат — контекст заполняется. Перед этим я обновлю PROJECT.md с тем, что мы сделали сегодня. Хочешь, чтобы я это сделал прямо сейчас?"

Then update this file with:
- What was built/committed
- Current state of the code
- What should be done next
- Any important decisions made

### Key decisions already made
- All UI responses to parent: **Russian**
- Worksheet content language: selectable ES / VAL
- Data format: embedded JSON (later: separate .json files)
- Start with self-contained single `index.html`

---

## Changelog
| Date | What happened |
|------|--------------|
| 2026-06-09 | Project started. PROJECT.md created. Worksheet generator in progress. |
