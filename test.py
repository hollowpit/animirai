from src.sources.comickio import Comick
scraper = Comick()
mangas = scraper.popular_manga()
manga = scraper.manga_details(mangas[5].id)
print(manga.get())