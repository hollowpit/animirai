from src.sources.asurascans import AsuraScans
import json
scraper = AsuraScans()
mangas = scraper.popular_manga()
for manga in mangas:
  print(json.dumps(manga.get(), indent=4))

chapter = mangas[0].chapter_ids["Chapter 1 -  "]
print(scraper.get_chapter(chapter).get())
print(mangas[0].get())