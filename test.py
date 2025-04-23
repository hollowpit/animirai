from src.sources.toonily import Toonily
import json

scraper = Toonily()

print("Testing popular manga:")
popular_mangas = scraper.popular_manga(1)
if popular_mangas:
    print(f"Found {len(popular_mangas)} popular manga")
    print(f"First manga: {popular_mangas[0].title}")
    print(f"Chapters: {popular_mangas[0].chapters}")
else:
    print("No popular manga found")

print("\nTesting latest manga:")
latest_mangas = scraper.latest_manga(1)
if latest_mangas:
    print(f"Found {len(latest_mangas)} latest manga")
    print(f"First manga: {latest_mangas[0].title}")
    print(f"Chapters: {latest_mangas[0].chapters}")
else:
    print("No latest manga found")

print("\nTesting search:")
search_mangas = scraper.search_manga("landlady")
if search_mangas:
    print(f"Found {len(search_mangas)} manga matching 'landlady'")
    print(f"First manga: {search_mangas[0].title}")
    print(f"Chapters: {search_mangas[0].chapters}")
    print(json.dumps(search_mangas[0].get()))
else:
    print("No matching manga found")