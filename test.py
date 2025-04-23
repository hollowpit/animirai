from src.sources.nhentainet import NHentai
import json
scraper = NHentai()
mangas = scraper.latest_manga()
print(len(mangas))

chapter = mangas[2].chapter_ids["Chapter 1"]
print(scraper.get_chapter(chapter).get())