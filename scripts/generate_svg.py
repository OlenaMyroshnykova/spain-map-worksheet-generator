"""
generate_svg.py

Downloads Spain province boundaries from a public GeoJSON source and builds
two clean SVG maps:

  maps/provinces.svg     — 52 provinces, each <path> coloured by community
  maps/communities.svg   — 19 autonomous communities (provinces dissolved)

Each <path> carries data attributes for future interactivity:
  id="province-{code}"           e.g. id="province-46"
  data-province-id="{id}"        e.g. data-province-id="valencia"
  data-community-code="{code}"   e.g. data-community-code="19"

Usage:
    pip install -r requirements.txt
    python scripts/generate_svg.py
"""

import io
import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

import geopandas as gpd
from shapely.geometry import GeometryCollection, MultiPolygon, Polygon, box as shapely_box

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = REPO_ROOT / "data" / "spain.json"
OUTPUT_PROVINCES = REPO_ROOT / "maps" / "provinces.svg"
OUTPUT_COMMUNITIES = REPO_ROOT / "maps" / "communities.svg"

GEOJSON_URL = (
    "https://raw.githubusercontent.com/"
    "codeforamerica/click_that_hood/master/public/data/spain-provinces.geojson"
)

# Natural Earth 50m country boundaries — used to draw Morocco + Algeria context.
AFRICA_GEOJSON_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
    "master/geojson/ne_50m_admin_0_countries.geojson"
)

# es-atlas TopoJSON — autonomous communities geometry (purpose-built, no dissolve needed).
COMMUNITIES_TOPOJSON_URL = (
    "https://cdn.jsdelivr.net/npm/es-atlas@0.6.0/es/autonomous_regions.json"
)

# Maps es-atlas community IDs → our spain.json community codes.
ES_ATLAS_TO_SPAIN_CODE = {
    "01": "01", "02": "02", "03": "18", "04": "03", "05": "04",
    "06": "05", "07": "07", "08": "06", "09": "08", "10": "19",
    "11": "10", "12": "11", "13": "13", "14": "15", "15": "16",
    "16": "17", "17": "12", "18": "09", "19": "14",
    # "20" = Gibraltar, omitted intentionally
}

# ---------------------------------------------------------------------------
# SVG canvas settings
# ---------------------------------------------------------------------------

SVG_WIDTH = 900
SVG_HEIGHT = 800

# Canary Islands are far west — render them in a small inset box below the mainland.
INSET_X = 10
INSET_Y = 705
INSET_WIDTH = 230
INSET_HEIGHT = 88

MAINLAND_BOUNDS = {
    "min_lon": -9.5,
    "max_lon": 4.4,
    "min_lat": 33.0,
    "max_lat": 43.8,
}

CANARY_BOUNDS = {
    "min_lon": -18.2,
    "max_lon": -13.3,
    "min_lat": 27.6,
    "max_lat": 29.5,
}

# Province codes that belong to the Canary Islands.
CANARY_PROVINCE_CODES = {"35", "38"}

# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------


def load_spain_data(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_community_color_map(spain_data: dict) -> dict[str, str]:
    """Return {communityCode: mapColor}."""
    return {c["code"]: c["mapColor"] for c in spain_data["autonomousCommunities"]}


def build_community_name_map(spain_data: dict) -> dict[str, str]:
    """Return {communityCode: castilian name}."""
    return {c["code"]: c["names"]["castilian"] for c in spain_data["autonomousCommunities"]}


def build_community_id_map(spain_data: dict) -> dict[str, str]:
    """Return {communityCode: community id}."""
    return {c["code"]: c["id"] for c in spain_data["autonomousCommunities"]}


def build_province_id_map(spain_data: dict) -> dict[str, str]:
    """Return {provinceCode: province id}."""
    return {p["code"]: p["id"] for p in spain_data["provinces"]}


def download_geojson(url: str) -> gpd.GeoDataFrame:
    print(f"  Downloading: {url}")
    with urllib.request.urlopen(url) as response:
        raw = response.read()
    return gpd.read_file(io.BytesIO(raw))


def download_communities_geojson() -> gpd.GeoDataFrame:
    """Download es-atlas autonomous regions TopoJSON and return as GeoDataFrame
    with a cod_ccaa column matching our spain.json community codes."""
    print(f"  Downloading: {COMMUNITIES_TOPOJSON_URL}")
    with urllib.request.urlopen(COMMUNITIES_TOPOJSON_URL) as response:
        raw = response.read()
    gdf = gpd.read_file(io.BytesIO(raw), driver="TopoJSON", layer="autonomous_regions")
    gdf = gdf[gdf["id"].isin(ES_ATLAS_TO_SPAIN_CODE)].copy()
    gdf["cod_ccaa"] = gdf["id"].map(ES_ATLAS_TO_SPAIN_CODE)
    print(f"  Loaded {len(gdf)} autonomous communities.")
    return gdf


def download_africa_context(url: str) -> "gpd.GeoDataFrame | None":
    """Download Natural Earth countries and return the Morocco + Algeria subset."""
    print(f"  Downloading Africa context: {url}")
    try:
        with urllib.request.urlopen(url) as response:
            raw = response.read()
        gdf = gpd.read_file(io.BytesIO(raw))
        for field in ("ADMIN", "admin", "NAME", "name"):
            if field in gdf.columns:
                subset = gdf[gdf[field].isin({"Morocco", "Algeria"})]
                if not subset.empty:
                    print(f"  Found {len(subset)} Africa context features (field='{field}').")
                    return subset
    except Exception as exc:
        print(f"  Warning: Africa context download failed ({exc}). Using fallback path.")
    return None


# ---------------------------------------------------------------------------
# Coordinate projection
# ---------------------------------------------------------------------------


def project_to_svg(
    lon: float,
    lat: float,
    bounds: dict,
    canvas_w: float,
    canvas_h: float,
    padding: float = 10,
) -> tuple[float, float]:
    """Convert geographic lon/lat to SVG pixel coordinates."""
    usable_w = canvas_w - 2 * padding
    usable_h = canvas_h - 2 * padding
    x = padding + (lon - bounds["min_lon"]) / (bounds["max_lon"] - bounds["min_lon"]) * usable_w
    y = padding + (bounds["max_lat"] - lat) / (bounds["max_lat"] - bounds["min_lat"]) * usable_h
    return round(x, 2), round(y, 2)


def polygon_to_path_data(
    polygon: Polygon,
    bounds: dict,
    canvas_w: float,
    canvas_h: float,
) -> str:
    """Convert a Shapely Polygon to SVG path data string."""

    def ring_commands(coords) -> str:
        commands = []
        for i, (lon, lat) in enumerate(coords):
            x, y = project_to_svg(lon, lat, bounds, canvas_w, canvas_h)
            commands.append(f"{'M' if i == 0 else 'L'}{x},{y}")
        commands.append("Z")
        return " ".join(commands)

    parts = [ring_commands(polygon.exterior.coords)]
    for interior in polygon.interiors:
        parts.append(ring_commands(interior.coords))
    return " ".join(parts)


def geometry_to_path_data(
    geometry,
    bounds: dict,
    canvas_w: float,
    canvas_h: float,
) -> str:
    """Convert a Shapely geometry to SVG path data (handles Polygon, MultiPolygon, GeometryCollection)."""
    if isinstance(geometry, Polygon):
        polys = [geometry]
    elif isinstance(geometry, MultiPolygon):
        polys = list(geometry.geoms)
    elif isinstance(geometry, GeometryCollection):
        # Flatten: keep only (Multi)Polygon parts (e.g. after an intersection)
        polys = []
        for g in geometry.geoms:
            if isinstance(g, Polygon):
                polys.append(g)
            elif isinstance(g, MultiPolygon):
                polys.extend(g.geoms)
    else:
        return ""
    return " ".join(polygon_to_path_data(p, bounds, canvas_w, canvas_h) for p in polys)


# ---------------------------------------------------------------------------
# SVG helpers
# ---------------------------------------------------------------------------


def make_svg_root() -> ET.Element:
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    return ET.Element("svg", {
        "xmlns": "http://www.w3.org/2000/svg",
        "viewBox": f"0 0 {SVG_WIDTH} {SVG_HEIGHT}",
        "width": str(SVG_WIDTH),
        "height": str(SVG_HEIGHT),
    })


SHARED_STYLE = (
    "path { stroke: #555; stroke-width: 0.6; stroke-linejoin: round; } "
    "path:hover { opacity: 0.8; cursor: pointer; } "
    "#africa-context path { stroke: #888; stroke-width: 0.5; pointer-events: none; } "
    "#africa-context path:hover { opacity: 1; cursor: default; } "
    ".inset-border { fill: none; stroke: #999; stroke-width: 1; stroke-dasharray: 4 3; } "
    ".inset-label { font-family: sans-serif; font-size: 9px; fill: #666; } "
)

# communities.svg uses no stroke on fill paths + a separate border overlay,
# so no province-boundary artifacts can appear inside community regions.
COMMUNITIES_STYLE = (
    "path { stroke: none; } "
    "path:hover { opacity: 0.8; cursor: pointer; } "
    "#community-borders path { fill: none; stroke: #555; stroke-width: 0.7; "
    "stroke-linejoin: round; pointer-events: none; } "
    "#africa-context path { stroke: #888; stroke-width: 0.5; pointer-events: none; } "
    "#africa-context path:hover { opacity: 1; cursor: default; } "
    ".inset-border { fill: none; stroke: #999; stroke-width: 1; stroke-dasharray: 4 3; } "
    ".inset-label { font-family: sans-serif; font-size: 9px; fill: #666; } "
)


def add_africa_strip(parent: ET.Element, africa_gdf: "gpd.GeoDataFrame | None" = None) -> None:
    """Add North Africa geographic context (Morocco + Algeria) clipped to map bounds."""
    group = ET.SubElement(parent, "g", {"id": "africa-context"})

    if africa_gdf is not None and not africa_gdf.empty:
        clip = shapely_box(
            MAINLAND_BOUNDS["min_lon"],
            MAINLAND_BOUNDS["min_lat"],
            MAINLAND_BOUNDS["max_lon"],
            MAINLAND_BOUNDS["max_lat"],
        )
        combined = africa_gdf.geometry.union_all()
        clipped = combined.intersection(clip)
        strip_d = geometry_to_path_data(clipped, MAINLAND_BOUNDS, SVG_WIDTH, SVG_HEIGHT)
    else:
        # Fallback: manually traced Morocco coastline for min_lat=35.3
        strip_d = (
            "M0,799 C80,797 160,790 220,762 "
            "C247,749 260,741 272,738 "
            "C280,737 292,742 315,752 "
            "C345,764 390,778 435,788 "
            "C470,793 510,797 560,799 "
            "C620,800 700,800 900,800 L0,800 Z"
        )

    ET.SubElement(group, "path", {
        "id": "africa-strip",
        "fill": "#CCCCCC",
        "d": strip_d,
    })


def add_inset_frame(parent: ET.Element, label: str) -> ET.Element:
    """Add the Canary Islands inset box and return a <g> to place paths in."""
    group = ET.SubElement(parent, "g", {"id": "canary-islands-inset"})
    ET.SubElement(group, "rect", {
        "x": str(INSET_X),
        "y": str(INSET_Y),
        "width": str(INSET_WIDTH),
        "height": str(INSET_HEIGHT),
        "class": "inset-border",
    })
    text = ET.SubElement(group, "text", {
        "x": str(INSET_X + 4),
        "y": str(INSET_Y + INSET_HEIGHT - 4),
        "class": "inset-label",
    })
    text.text = label
    return group


def is_canary_province(code: str) -> bool:
    return code in CANARY_PROVINCE_CODES


def add_path(
    parent: ET.Element,
    path_data: str,
    attributes: dict,
    is_inset: bool = False,
) -> None:
    attrs = {**attributes, "d": path_data}
    if is_inset:
        attrs["transform"] = f"translate({INSET_X},{INSET_Y})"
    ET.SubElement(parent, "path", attrs)


# ---------------------------------------------------------------------------
# SVG builders
# ---------------------------------------------------------------------------


def build_provinces_svg(
    gdf: gpd.GeoDataFrame,
    community_colors: dict,
    province_ids: dict,
    africa_gdf: "gpd.GeoDataFrame | None" = None,
) -> ET.Element:
    """Build SVG with one <path> per province."""
    svg = make_svg_root()
    ET.SubElement(svg, "style").text = SHARED_STYLE
    add_africa_strip(svg, africa_gdf)

    mainland = ET.SubElement(svg, "g", {"id": "mainland"})
    inset = add_inset_frame(svg, "Islas Canarias")

    for _, row in gdf.iterrows():
        province_code = str(row["cod_prov"]).zfill(2)
        community_code = str(row["cod_ccaa"]).zfill(2)
        province_id = province_ids.get(province_code, province_code)
        fill = community_colors.get(community_code, "#CCCCCC")
        canary = is_canary_province(province_code)

        bounds = CANARY_BOUNDS if canary else MAINLAND_BOUNDS
        canvas_w = INSET_WIDTH if canary else SVG_WIDTH
        canvas_h = INSET_HEIGHT if canary else SVG_HEIGHT

        path_data = geometry_to_path_data(row.geometry, bounds, canvas_w, canvas_h)
        attrs = {
            "id": f"province-{province_code}",
            "data-province-id": province_id,
            "data-community-code": community_code,
            "fill": fill,
        }
        add_path(inset if canary else mainland, path_data, attrs, is_inset=canary)

    return svg


def build_communities_svg(
    communities_gdf: gpd.GeoDataFrame,
    community_colors: dict,
    community_ids: dict,
    africa_gdf: "gpd.GeoDataFrame | None" = None,
) -> ET.Element:
    """Build SVG with one <path> per autonomous community (es-atlas source)."""

    svg = make_svg_root()
    ET.SubElement(svg, "style").text = COMMUNITIES_STYLE
    add_africa_strip(svg, africa_gdf)

    mainland = ET.SubElement(svg, "g", {"id": "mainland"})
    inset = add_inset_frame(svg, "Islas Canarias")

    for _, row in communities_gdf.iterrows():
        community_code = str(row["cod_ccaa"]).zfill(2)
        community_id = community_ids.get(community_code, community_code)
        fill = community_colors.get(community_code, "#CCCCCC")

        is_canary = community_code == "04"

        bounds = CANARY_BOUNDS if is_canary else MAINLAND_BOUNDS
        canvas_w = INSET_WIDTH if is_canary else SVG_WIDTH
        canvas_h = INSET_HEIGHT if is_canary else SVG_HEIGHT

        path_data = geometry_to_path_data(row.geometry, bounds, canvas_w, canvas_h)
        attrs = {
            "id": f"community-{community_code}",
            "data-community-id": community_id,
            "data-community-code": community_code,
            "fill": fill,
        }
        add_path(inset if is_canary else mainland, path_data, attrs, is_inset=is_canary)

    # Border overlay: draw community outlines on top with no fill.
    # Since community fill paths have stroke:none, ONLY this overlay draws borders —
    # province lines can never bleed through.
    borders = ET.SubElement(svg, "g", {"id": "community-borders"})
    for _, row in communities_gdf.iterrows():
        community_code = str(row["cod_ccaa"]).zfill(2)
        is_canary = community_code == "04"
        bounds = CANARY_BOUNDS if is_canary else MAINLAND_BOUNDS
        canvas_w = INSET_WIDTH if is_canary else SVG_WIDTH
        canvas_h = INSET_HEIGHT if is_canary else SVG_HEIGHT
        path_data = geometry_to_path_data(row.geometry, bounds, canvas_w, canvas_h)
        attrs: dict = {"fill": "none", "d": path_data}
        if is_canary:
            attrs["transform"] = f"translate({INSET_X},{INSET_Y})"
        ET.SubElement(borders, "path", attrs)

    return svg


# ---------------------------------------------------------------------------
# File writer
# ---------------------------------------------------------------------------


def write_svg(element: ET.Element, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tree = ET.ElementTree(element)
    ET.indent(tree, space="  ")
    tree.write(path, encoding="unicode", xml_declaration=False)
    size_kb = path.stat().st_size // 1024
    print(f"  Saved: {path}  ({size_kb} KB)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(communities_only: bool = False) -> None:
    print("=== Spain SVG Map Generator ===\n")

    if not DATA_FILE.exists():
        print(f"ERROR: data file not found: {DATA_FILE}")
        sys.exit(1)

    spain_data = load_spain_data(DATA_FILE)
    community_colors = build_community_color_map(spain_data)
    community_ids = build_community_id_map(spain_data)
    province_ids = build_province_id_map(spain_data)

    print("Downloading Africa context (Morocco + Algeria)...")
    africa_gdf = download_africa_context(AFRICA_GEOJSON_URL)

    if not communities_only:
        print("\nDownloading province boundaries...")
        prov_gdf = download_geojson(GEOJSON_URL)
        print(f"  Loaded {len(prov_gdf)} provinces.")
        print("\nBuilding provinces.svg...")
        provinces_svg = build_provinces_svg(prov_gdf, community_colors, province_ids, africa_gdf)
        write_svg(provinces_svg, OUTPUT_PROVINCES)

    print("\nDownloading community boundaries (es-atlas)...")
    comm_gdf = download_communities_geojson()
    print("\nBuilding communities.svg...")
    communities_svg = build_communities_svg(comm_gdf, community_colors, community_ids, africa_gdf)
    write_svg(communities_svg, OUTPUT_COMMUNITIES)

    print("\nDone.")


if __name__ == "__main__":
    main(communities_only="--communities" in sys.argv)
