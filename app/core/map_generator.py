class MapGenerator:
    def __init__(self, geo_provider, projection, svg_builder):
        self.geo = geo_provider
        self.projection = projection
        self.svg = svg_builder

    def generate(self):
        gdf = self.geo.load()

        for _, row in gdf.iterrows():
            geom = row.geometry

            # placeholder conversion (keep simple for now)
            if hasattr(geom, "exterior"):
                coords = list(geom.exterior.coords)
                path = " ".join([f"L{x},{y}" for x, y in coords])
                path = "M" + path
            else:
                continue

            self.svg.add_path(path, {
                "class": "province",
                "data-id": str(row.get("name", "unknown"))
            })

        return self.svg.build()