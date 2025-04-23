from src.sources.comickio import Comick
scraper = Comick()
mangas = scraper.popular_manga()
for manga in mangas:
    print(manga.url)

print(len(mangas))