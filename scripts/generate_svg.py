"""
generate_svg.py

Downloads Spain province boundaries from a public GeoJSON source,
merges them with data from spain.json, and saves a clean SVG map
to maps/spain.svg.

Each province <path> in the output SVG has:
  - id="province-{code}"            e.g. id="province-46"
  - data-province-id="{id}"         e.g. data-province-id="valencia"
  - data-community-code="{code}"    e.g. data-community-code="19"
  - fill set to the community color from spain.json

Usage:
    pip install -r requirements.txt
    python scripts/generate_svg.py
"""

import json
import os
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

import geopandas as gpd
from shapely.geometry import MultiPolygon, Polygon

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = REPO_ROOT / "data" / "spain.json"
OUTPUT_FILE = REPO_ROOT / "maps" / "spain.svg"

GEOJSON_URL = (
    "https://raw.githubusercontent.com/"
    "codeforamerica/click_that_hood/master/public/data/spain-provinces.geojson"
)

# ---------------------------------------------------------------------------
# SVG canvas settings
# ---------------------------------------------------------------------------

SVG_WIDTH = 900
SVG_HEIGHT = 700

# Canary Islands are far from the mainland so we render them in an inset box.
INSET_X = 30
INSET_Y = 530
INSET_WIDTH = 200
INSET_HEIGHT = 130

# Approximate bounding box of mainland Spain + Baleares (longitude, latitude).
MAINLAND_BOUNDS = {
    "min_lon": -9.5,
    "max_lon": 4.4,
    "min_lat": 35.8,
    "max_lat": 43.8,
}

# Approximate bounding box of the Canary Islands.
CANARY_BOUNDS = {
    "min_lon": -18.2,
    "max_lon": -13.3,
    "min_lat": 27.6,
    "max_lat": 29.5,
}

# Province codes that belong to the Canary Islands.
CANARY_PROVINCE_CODES = {"35", "38"}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_spain_data(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_community_color_map(spain_data: dict) -> dict[str, str]:
    """Return {communityCode: mapColor} from spain.json."""
    return {
        community["code"]: community["mapColor"]
        for community in spain_data["autonomousCommunities"]
    }


def build_province_id_map(spain_data: dict) -> dict[str, str]:
    """Return {provinceCode: provinceId} from spain.json."""
    return {
        province["code"]: province["id"]
        for province in spain_data["provinces"]
    }


def download_geojson(url: str) -> gpd.GeoDataFrame:
    print(f"Downloading province boundaries from:\n  {url}")
    with urllib.request.urlopen(url) as response:
        raw = response.read()
    import io
    return gpd.read_file(io.BytesIO(raw))


def project_to_svg(lon: float, lat: float, bounds: dict, canvas_w: float, canvas_h: float) -> tuple[float, float]:
    """
    Convert geographic coordinates to SVG pixel coordinates.
    Latitude is flipped because SVG y-axis grows downward.
    Adds a small padding so shapes don't touch the canvas edge.
    """
    padding = 10
    usable_w = canvas_w - 2 * padding
    usable_h = canvas_h - 2 * padding

    x = padding + (lon - bounds["min_lon"]) / (bounds["max_lon"] - bounds["min_lon"]) * usable_w
    y = padding + (bounds["max_lat"] - lat) / (bounds["max_lat"] - bounds["min_lat"]) * usable_h
    return round(x, 2), round(y, 2)


def polygon_to_svg_path(polygon: Polygon, bounds: dict, canvas_w: float, canvas_h: float) -> str:
    """Convert a Shapely Polygon to an SVG path data string."""
    parts = []

    def ring_to_commands(coords) -> str:
        commands = []
        for i, (lon, lat) in enumerate(coords):
            x, y = project_to_svg(lon, lat, bounds, canvas_w, canvas_h)
            cmd = "M" if i == 0 else "L"
            commands.append(f"{cmd}{x},{y}")
        commands.append("Z")
        return " ".join(commands)

    parts.append(ring_to_commands(polygon.exterior.coords))
    for interior in polygon.interiors:
        parts.append(ring_to_commands(interior.coords))

    return " ".join(parts)


def geometry_to_svg_path(geometry, bounds: dict, canvas_w: float, canvas_h: float) -> str:
    """Convert a Shapely geometry (Polygon or MultiPolygon) to SVG path data."""
    if isinstance(geometry, Polygon):
        polygons = [geometry]
    elif isinstance(geometry, MultiPolygon):
        polygons = list(geometry.geoms)
    else:
        return ""

    return " ".join(
        polygon_to_svg_path(p, bounds, canvas_w, canvas_h)
        for p in polygons
    )


# ---------------------------------------------------------------------------
# SVG builder
# ---------------------------------------------------------------------------


def build_svg(gdf: gpd.GeoDataFrame, community_colors: dict, province_ids: dict) -> ET.Element:
    ET.register_namespace("", "http://www.w3.org/2000/svg")

    svg = ET.Element("svg", {
        "xmlns": "http://www.w3.org/2000/svg",
        "viewBox": f"0 0 {SVG_WIDTH} {SVG_HEIGHT}",
        "width": str(SVG_WIDTH),
        "height": str(SVG_HEIGHT),
    })

    # Style block
    style = ET.SubElement(svg, "style")
    style.text = (
        "path { stroke: #555; stroke-width: 0.6; stroke-linejoin: round; } "
        "path:hover { opacity: 0.8; cursor: pointer; } "
        ".inset-border { fill: none; stroke: #999; stroke-width: 1; stroke-dasharray: 4 3; } "
        ".inset-label { font-family: sans-serif; font-size: 9px; fill: #666; } "
    )

    # --- Mainland + Baleares group ---
    mainland_group = ET.SubElement(svg, "g", {"id": "mainland"})

    # --- Canary Islands inset group ---
    inset_group = ET.SubElement(svg, "g", {"id": "canary-islands-inset"})

    # Inset border rectangle
    ET.SubElement(inset_group, "rect", {
        "x": str(INSET_X),
        "y": str(INSET_Y),
        "width": str(INSET_WIDTH),
        "height": str(INSET_HEIGHT),
        "class": "inset-border",
    })

    # Inset label
    label = ET.SubElement(inset_group, "text", {
        "x": str(INSET_X + 4),
        "y": str(INSET_Y + INSET_HEIGHT - 4),
        "class": "inset-label",
    })
    label.text = "Islas Canarias"

    # --- Render each province ---
    for _, row in gdf.iterrows():
        province_code = str(row["cod_prov"]).zfill(2)
        community_code = str(row["cod_ccaa"]).zfill(2)
        province_id = province_ids.get(province_code, province_code)
        fill_color = community_colors.get(community_code, "#CCCCCC")

        is_canary = province_code in CANARY_PROVINCE_CODES

        if is_canary:
            path_data = geometry_to_svg_path(
                row.geometry, CANARY_BOUNDS, INSET_WIDTH, INSET_HEIGHT
            )
            # Offset path into the inset box
            path_element = ET.SubElement(inset_group, "path", {
                "id": f"province-{province_code}",
                "data-province-id": province_id,
                "data-community-code": community_code,
                "d": path_data,
                "fill": fill_color,
                "transform": f"translate({INSET_X},{INSET_Y})",
            })
        else:
            path_data = geometry_to_svg_path(
                row.geometry, MAINLAND_BOUNDS, SVG_WIDTH, SVG_HEIGHT
            )
            ET.SubElement(mainland_group, "path", {
                "id": f"province-{province_code}",
                "data-province-id": province_id,
                "data-community-code": community_code,
                "d": path_data,
                "fill": fill_color,
            })

    return svg


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    print("=== Spain SVG Map Generator ===\n")

    if not DATA_FILE.exists():
        print(f"ERROR: data file not found at {DATA_FILE}")
        sys.exit(1)

    spain_data = load_spain_data(DATA_FILE)
    community_colors = build_community_color_map(spain_data)
    province_ids = build_province_id_map(spain_data)

    gdf = download_geojson(GEOJSON_URL)
    print(f"Loaded {len(gdf)} provinces.\n")

    svg_element = build_svg(gdf, community_colors, province_ids)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    tree = ET.ElementTree(svg_element)
    ET.indent(tree, space="  ")
    tree.write(OUTPUT_FILE, encoding="unicode", xml_declaration=False)

    print(f"SVG saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
