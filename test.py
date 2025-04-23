from src.sources.comickio import Comick
import json
scraper = Comick()
mangas = scraper.latest_manga()
print(mangas[99].get())
manga = scraper.manga_details(mangas[5].id)
print(manga.get())
print(json.dumps(manga.chapter_and_pages, indent=4))