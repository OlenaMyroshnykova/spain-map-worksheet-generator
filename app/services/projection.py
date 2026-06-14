class EquirectangularProjection:
    def __init__(self, width, height, bounds):
        self.width = width
        self.height = height
        self.minx, self.miny, self.maxx, self.maxy = bounds

    def project(self, lon, lat):
        x = (lon - self.minx) / (self.maxx - self.minx) * self.width
        y = self.height - (lat - self.miny) / (self.maxy - self.miny) * self.height
        return x, y