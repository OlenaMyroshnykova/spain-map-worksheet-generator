from app.core.generator import MapGenerator

def main():
    gen = MapGenerator()
    result = gen.create('data/spain.geojson')
    print(result)

if __name__ == '__main__':
    main()
