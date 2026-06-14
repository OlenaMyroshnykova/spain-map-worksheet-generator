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
from shapely.geometry import GeometryCollection, MultiPolygon, Point, Polygon, box as shapely_box
from shapely.ops import transform as shapely_transform

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

# Canary Islands inset — bottom edge aligned with Africa strip bottom (y=790), left of Spain.
INSET_X = 10
INSET_Y = 702   # Spain's southernmost mainland point is at y≈701
INSET_WIDTH = 265
INSET_HEIGHT = 88  # 702 + 88 = 790 = Africa strip bottom edge

MAINLAND_BOUNDS = {
    "min_lon": -9.5,
    "max_lon": 4.4,
    "min_lat": 35.0,
    "max_lat": 43.8,
}

CANARY_BOUNDS = {
    "min_lon": -18.5,  # slight padding around islands
    "max_lon": -13.0,
    "min_lat": 27.3,
    "max_lat": 29.8,
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
    """Download Natural Earth countries and return Morocco, Algeria and Portugal."""
    print(f"  Downloading neighbor context: {url}")
    try:
        with urllib.request.urlopen(url) as response:
            raw = response.read()
        gdf = gpd.read_file(io.BytesIO(raw))
        for field in ("ADMIN", "admin", "NAME", "name"):
            if field in gdf.columns:
                subset = gdf[gdf[field].isin({"Morocco", "Algeria", "Portugal"})]
                if not subset.empty:
                    gdf._name_field = field  # stash for use in add_africa_strip
                    subset = subset.copy()
                    subset["_name"] = subset[field]
                    print(f"  Found {len(subset)} neighbor features (field='{field}').")
                    return subset
    except Exception as exc:
        print(f"  Warning: Neighbor context download failed ({exc}). Using fallback path.")
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
    # Filter out micro-sliver artifacts (area < 1e-4 sq geographic degrees)
    polys = [p for p in polys if p.area >= 1e-4]
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
    ".inset-label { font-family: "Segoe UI", Arial, sans-serif; font-size: 14px; font-weight: 600; fill: #1a202c; } "
)


def add_africa_strip(parent: ET.Element, africa_gdf: "gpd.GeoDataFrame | None" = None) -> None:
    """Add Morocco/Algeria outline and Portugal outline, clipped to map bounds."""
    group = ET.SubElement(parent, "g", {"id": "africa-context"})

    clip = shapely_box(
        MAINLAND_BOUNDS["min_lon"],
        MAINLAND_BOUNDS["min_lat"],
        MAINLAND_BOUNDS["max_lon"],
        MAINLAND_BOUNDS["max_lat"],
    )

    if africa_gdf is not None and not africa_gdf.empty and "_name" in africa_gdf.columns:
        # Morocco + Algeria → africa-strip
        africa = africa_gdf[africa_gdf["_name"].isin({"Morocco", "Algeria"})]
        if not africa.empty:
            geom = africa.geometry.union_all().intersection(clip)
            d = geometry_to_path_data(geom, MAINLAND_BOUNDS, SVG_WIDTH, SVG_HEIGHT)
        else:
            d = ""
        ET.SubElement(group, "path", {"id": "africa-strip", "fill": "none", "d": d})

        # Portugal → separate outline path
        portugal = africa_gdf[africa_gdf["_name"] == "Portugal"]
        if not portugal.empty:
            geom = portugal.geometry.union_all().intersection(clip)
            d = geometry_to_path_data(geom, MAINLAND_BOUNDS, SVG_WIDTH, SVG_HEIGHT)
            if d:
                ET.SubElement(group, "path", {"id": "portugal-outline", "fill": "none", "d": d})
    else:
        # Fallback: Morocco coast only
        fallback_d = (
            "M234,730 L247,718 L261,714 L270,709 L277,711 "
            "L274,720 L279,730 L318,751 L337,755 L360,749 "
            "L418,743 L424,740 L426,745 L430,754 L445,758 "
            "L491,759 L506,752 L535,730 L553,718 L584,704 "
            "L621,689 L644,674 L736,653 L775,651 L835,637 "
            "L890,629 L890,790 L56,790 Z"
        )
        ET.SubElement(group, "path", {"id": "africa-strip", "fill": "none", "d": fallback_d})


def add_inset_frame(parent: ET.Element, label: str) -> ET.Element:
    """Add the Canary Islands inset box and return a <g> to place paths in."""
    group = ET.SubElement(parent, "g", {"id": "canary-islands-inset"})
    # White background so the inset overlays any province paths cleanly
    ET.SubElement(group, "rect", {
        "x": str(INSET_X),
        "y": str(INSET_Y),
        "width": str(INSET_WIDTH),
        "height": str(INSET_HEIGHT),
        "fill": "white",
    })
    ET.SubElement(group, "rect", {
        "x": str(INSET_X),
        "y": str(INSET_Y),
        "width": str(INSET_WIDTH),
        "height": str(INSET_HEIGHT),
        "class": "inset-border",
    })
    if label:
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
# Precomputed label layouts
# ---------------------------------------------------------------------------

PROVINCE_LABEL_OVERRIDES = {
    "03": {"dx": 0.6, "dy": 0.8},
    "12": {"dx": -0.4, "dy": -0.8},
    "28": {"dx": 0.0, "dy": 0.6},
    "08": {"dx": -0.5, "dy": -0.2},
    "43": {"dx": 0.2, "dy": -0.7},
    "48": {"dx": -4.2, "dy": -8.0},
    "20": {"dx": 4.8, "dy": -0.8},
    "01": {"dx": 0.0, "dy": 3.2},
    "35": {"font_size": 14},
    "38": {"font_size": 14},
    "51": {"font_size": 14},
    "52": {"font_size": 14},
}

ISLAND_PROVINCE_CODES = {"07", "35", "38"}

COMMUNITY_LABEL_OVERRIDES = {
    # Tiny/narrow regions and detached insets need explicit layouts.
    "04": {
        # The Canary Islands name is rendered as the larger inset caption,
        # not over the islands themselves.
        "hide_label": True,
    },
    "09": {
        "font_size": 13.5,
        "x": 340.0,
        "y": 708.0,
        "lines": {
            "castilian": ["Ciudad Autónoma", "de Ceuta"],
            "valencian": ["Ciutat Autònoma", "de Ceuta"],
        },
    },
    "14": {
        "font_size": 13.5,
        "x": 495.0,
        "y": 758.0,
        "lines": {
            "castilian": ["Ciudad Autónoma", "de Melilla"],
            "valencian": ["Ciutat Autònoma", "de Melilla"],
        },
    },
    "16": {
        "font_size": 12.5,
        "x": 517.0,
        "y": 120.0,
        "lines": {
            "castilian": ["Comunidad", "Foral de", "Navarra"],
            "valencian": ["Comunitat", "Foral de", "Navarra"],
        },
    },
}

def project_geometry_to_svg(geometry, bounds, canvas_w, canvas_h, tx=0, ty=0):
    def fn(x, y, z=None):
        px, py = project_to_svg(x, y, bounds, canvas_w, canvas_h)
        return px + tx, py + ty
    return shapely_transform(fn, geometry)

def estimate_text_width(text: str, size: float) -> float:
    width = 0.0
    for ch in text:
        if ch.isspace(): width += 0.32
        elif ch in "ilIíìïî|.,'": width += 0.30
        elif ch in "mwMWÁÀÉÈÓÒÚÙÑ": width += 0.82
        else: width += 0.57
    return width * size

def line_variants(label: str):
    words = label.split()
    variants = [[label]]
    for split in range(1, len(words)):
        variants.append([" ".join(words[:split]), " ".join(words[split:])])
    return sorted(variants, key=lambda lines: max(map(len, lines)) - min(map(len, lines)))

def fit_ratio(geom, cx, cy, width, height):
    hw, hh = width / 2 + .25, height / 2 + .25
    samples = [(0,0,4),(-.5,0,3),(.5,0,3),(0,-.5,3),(0,.5,3),
               (-.5,-.5,2),(.5,-.5,2),(-.5,.5,2),(.5,.5,2),
               (-1,0,2),(1,0,2),(0,-1,2),(0,1,2),
               (-1,-1,1),(1,-1,1),(-1,1,1),(1,1,1),
               (-1,-.5,1),(-1,.5,1),(1,-.5,1),(1,.5,1),
               (-.5,-1,1),(.5,-1,1),(-.5,1,1),(.5,1,1)]
    total = sum(w for _,_,w in samples)
    inside = sum(w for xr,yr,w in samples if geom.covers(Point(cx+xr*hw, cy+yr*hh)))
    return inside / total

def local_clearance(geom, cx, cy, max_distance=12, step=1.5):
    dirs=((1,0),(-1,0),(0,1),(0,-1),(.707,.707),(.707,-.707),(-.707,.707),(-.707,-.707))
    total=0.0
    for dx,dy in dirs:
        distance=0.0
        d=step
        while d <= max_distance + 1e-9:
            if not geom.covers(Point(cx+dx*d, cy+dy*d)): break
            distance=d; d += step
        total += distance
    return total/len(dirs)

def contour_label_layout(geom, label, max_font=14.0, min_font=6.0):
    minx,miny,maxx,maxy=geom.bounds
    bw,bh=maxx-minx,maxy-miny
    if bw <= 0 or bh <= 0: return None
    center_x,center_y=(minx+maxx)/2,(miny+maxy)/2
    shortest=min(bw,bh); diagonal=max(1.0,(bw*bw+bh*bh)**.5)
    coarse=max(.85, shortest/24)
    variants=line_variants(label)
    size=max_font
    while size >= min_font-.001:
        best=None
        for lines in variants:
            width=max(estimate_text_width(x,size) for x in lines)
            height=max(size,len(lines)*size*1.2)
            if width > bw*1.18 or height > bh*1.18: continue
            required=.74 if len(lines)>1 else .70
            y=miny+coarse/2
            while y <= maxy:
                x=minx+coarse/2
                while x <= maxx:
                    if geom.covers(Point(x,y)):
                        ratio=fit_ratio(geom,x,y,width,height)
                        if ratio >= required:
                            clearance=local_clearance(geom,x,y,min(16,shortest*.65),max(.8,coarse*.75))
                            dist=((x-center_x)**2+(y-center_y)**2)**.5/diagonal
                            imbalance=abs(len(lines[0])-len(lines[1])) if len(lines)>1 else 0
                            score=ratio*130+clearance*2.1-dist*20-imbalance*.45-(1.5 if len(lines)>1 else 0)
                            if best is None or score>best[0]: best=(score,x,y,lines)
                    x += coarse
                y += coarse
        if best:
            return {"x":best[1],"y":best[2],"size":round(size,2),"lines":best[3]}
        size=round(size-.25,2)
    rp=geom.representative_point()
    return {"x":rp.x,"y":rp.y,"size":min_font,"lines":[label]}

def add_precomputed_labels(svg, entries, topic):
    root=ET.SubElement(svg,"g",{"id":"precomputed-labels","style":"display:none;pointer-events:none"})
    for entry in entries:
        item=entry["item"]; geom=entry["geometry"]; code=item["code"]
        override = PROVINCE_LABEL_OVERRIDES.get(code, {}) if topic == "provinces" else COMMUNITY_LABEL_OVERRIDES.get(code, {})
        minx,miny,maxx,maxy=geom.bounds
        nx=(minx+maxx)/2 + override.get("dx",0); ny=(miny+maxy)/2 + override.get("dy",0)
        meta=ET.SubElement(root,"g",{"data-label-id":item["id"],"data-number-x":str(round(nx,2)),"data-number-y":str(round(ny,2))})
        if override.get("hide_label"):
            continue
        for lang in ("castilian","valencian"):
            label=item["names"][lang]
            explicit_lines = override.get("lines", {}).get(lang)
            if explicit_lines:
                layout = {
                    "x": override["x"],
                    "y": override["y"],
                    "size": override["font_size"],
                    "lines": explicit_lines,
                }
            elif topic == "provinces" and code in ISLAND_PROVINCE_CODES:
                rp = geom.representative_point()
                layout = {"x": rp.x, "y": rp.y, "size": override.get("font_size", 14), "lines": [label]}
            else:
                max_font = 18 if topic == "communities" else 14
                min_font = 9 if topic == "communities" else 6
                layout = contour_label_layout(geom, label, max_font, min_font)
                if "font_size" in override:
                    layout["size"] = override["font_size"]
                if "x" in override:
                    layout["x"] = override["x"]
                if "y" in override:
                    layout["y"] = override["y"]
            layout["x"] += override.get("dx", 0)
            layout["y"] += override.get("dy", 0)
            lg=ET.SubElement(meta,"g",{"data-lang":lang,"data-x":str(round(layout["x"],2)),"data-y":str(round(layout["y"],2)),"data-font-size":str(layout["size"]),"data-lines":"|".join(layout["lines"])})
            lg.text = " "  # Keep explicit <g></g>; SVG is later parsed through HTML innerHTML.
    return root

# ---------------------------------------------------------------------------
# SVG builders
# ---------------------------------------------------------------------------


def build_provinces_svg(
    gdf: gpd.GeoDataFrame,
    community_colors: dict,
    province_ids: dict,
    spain_data: dict,
    africa_gdf: "gpd.GeoDataFrame | None" = None,
) -> ET.Element:
    """Build SVG with one <path> per province."""
    svg = make_svg_root()
    ET.SubElement(svg, "style").text = SHARED_STYLE
    add_africa_strip(svg, africa_gdf)

    mainland = ET.SubElement(svg, "g", {"id": "mainland"})
    inset = add_inset_frame(svg, "Islas Canarias")
    label_entries = []

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
        projected = project_geometry_to_svg(row.geometry, bounds, canvas_w, canvas_h, INSET_X if canary else 0, INSET_Y if canary else 0)
        item = next((p for p in spain_data["provinces"] if p["code"] == province_code), None)
        if item: label_entries.append({"item": item, "geometry": projected})

    add_precomputed_labels(svg, label_entries, "provinces")
    add_enclave_markers(svg)
    return svg


def build_communities_svg(
    communities_gdf: gpd.GeoDataFrame,
    community_colors: dict,
    community_ids: dict,
    spain_data: dict,
    africa_gdf: "gpd.GeoDataFrame | None" = None,
) -> ET.Element:
    """Build SVG with one <path> per autonomous community (es-atlas source)."""

    svg = make_svg_root()
    ET.SubElement(svg, "style").text = COMMUNITIES_STYLE
    add_africa_strip(svg, africa_gdf)

    mainland = ET.SubElement(svg, "g", {"id": "mainland"})
    inset = add_inset_frame(svg, "Islas Canarias")
    label_entries = []

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
        projected = project_geometry_to_svg(row.geometry, bounds, canvas_w, canvas_h, INSET_X if is_canary else 0, INSET_Y if is_canary else 0)
        item = next((c for c in spain_data["autonomousCommunities"] if c["code"] == community_code), None)
        if item: label_entries.append({"item": item, "geometry": projected})

    add_precomputed_labels(svg, label_entries, "communities")

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

    add_enclave_markers(svg)
    return svg


# ---------------------------------------------------------------------------
# File writer
# ---------------------------------------------------------------------------


def add_enclave_markers(svg: ET.Element) -> None:
    """Add small bracket tick marks around Ceuta and Melilla to separate them from Africa."""
    # Compute SVG pixel positions from geographic coordinates
    ceuta_lon, ceuta_lat = -5.31, 35.89
    melilla_lon, melilla_lat = -2.95, 35.29
    cx, cy = project_to_svg(ceuta_lon, ceuta_lat, MAINLAND_BOUNDS, SVG_WIDTH, SVG_HEIGHT)
    mx, my = project_to_svg(melilla_lon, melilla_lat, MAINLAND_BOUNDS, SVG_WIDTH, SVG_HEIGHT)

    group = ET.SubElement(svg, "g", {
        "id": "enclave-markers",
        "style": "stroke:#777;stroke-width:1.3;pointer-events:none",
    })
    for px, py in [(cx, cy), (mx, my)]:
        ET.SubElement(group, "line", {
            "x1": str(round(px - 8, 1)), "y1": str(round(py - 6, 1)),
            "x2": str(round(px - 8, 1)), "y2": str(round(py + 6, 1)),
        })
        ET.SubElement(group, "line", {
            "x1": str(round(px + 8, 1)), "y1": str(round(py - 6, 1)),
            "x2": str(round(px + 8, 1)), "y2": str(round(py + 6, 1)),
        })


def write_svg(element: ET.Element, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tree = ET.ElementTree(element)
    ET.indent(tree, space="  ")

    # ElementTree may introduce an ``ns0:`` prefix when an existing SVG
    # with a default namespace was parsed and then modified. The browser
    # inserts these files through HTML ``innerHTML``; tags such as
    # ``<ns0:style>`` are then treated as unknown HTML elements and their
    # CSS is rendered as visible text. Serialize and normalise the SVG back
    # to a plain default namespace so all tags remain native SVG elements.
    svg_text = ET.tostring(element, encoding="unicode")
    svg_text = svg_text.replace("<ns0:", "<").replace("</ns0:", "</")
    svg_text = svg_text.replace(
        'xmlns:ns0="http://www.w3.org/2000/svg"',
        'xmlns="http://www.w3.org/2000/svg"',
    )
    path.write_text(svg_text, encoding="utf-8")

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
        provinces_svg = build_provinces_svg(prov_gdf, community_colors, province_ids, spain_data, africa_gdf)
        write_svg(provinces_svg, OUTPUT_PROVINCES)

    print("\nDownloading community boundaries (es-atlas)...")
    comm_gdf = download_communities_geojson()
    print("\nBuilding communities.svg...")
    communities_svg = build_communities_svg(comm_gdf, community_colors, community_ids, spain_data, africa_gdf)
    write_svg(communities_svg, OUTPUT_COMMUNITIES)

    print("\nDone.")


if __name__ == "__main__":
    main(communities_only="--communities" in sys.argv)
