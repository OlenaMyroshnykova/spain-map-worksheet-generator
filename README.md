# Spain Map Worksheet Generator

Educational geography trainer for children — printable worksheets with maps of Spain.
Inspired by [edufichas.com](https://www.edufichas.com), built to grow into a Duolingo-style interactive app.

## What it does

Generates printable worksheets for learning:
- Provinces and autonomous communities of Spain
- Their capitals and locations on the map
- In two languages: Castilian and Valencian

## Roadmap

- **Step 1 (now):** Printable PDF worksheets — label the map, color by instructions
- **Step 2:** Interactive browser app — click to answer, instant feedback
- **Step 3:** Gamification — progress tracking, streaks, scoring

## Future topics

- European countries — flags and capitals
- Regions of Ukraine in Ukrainian
- Full political map of the world

## Project structure

```
data/
  spain.json          ← geographic data in Castilian and Valencian
scripts/
  generate_svg.py     ← builds SVG map from GeoJSON source
maps/
  spain.svg           ← generated map (run the script to create)
worksheets/           ← generated PDF worksheets (coming in step 2)
index.html            ← browser worksheet generator (coming in step 2)
```

## Setup

```bash
pip install -r requirements.txt
python scripts/generate_svg.py
```

The script downloads province boundaries from a public GeoJSON source,
combines them with data from `data/spain.json`, and saves a clean SVG to `maps/spain.svg`.
