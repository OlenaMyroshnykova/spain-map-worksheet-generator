import geopandas as gpd

class GeoJsonProvider:
    def __init__(self, url: str):
        self.url = url

    def load(self):
        return gpd.read_file(self.url)