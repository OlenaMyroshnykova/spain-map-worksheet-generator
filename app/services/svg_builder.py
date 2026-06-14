class SvgBuilder:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.paths = []

    def add_path(self, d, attrs):
        self.paths.append((d, attrs))

    def build(self):
        svg = [f'<svg width="{self.width}" height="{self.height}" xmlns="http://www.w3.org/2000/svg">']
        for d, attrs in self.paths:
            attr_str = " ".join([f'{k}=\"{v}\"' for k, v in attrs.items()])
            svg.append(f'<path d=\"{d}\" {attr_str}/>')
        svg.append("</svg>")
        return "\n".join(svg)