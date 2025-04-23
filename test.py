from src.sources.toonily import Toonily
scraper = Toonily()
mangas = scraper.popular_manga()
for manga in mangas:
    print(manga.get())