from src.sources.asurascans import AsuraScans
import json
scraper = AsuraScans()
mangas = scraper.popular_manga()
for manga in mangas:
  print(json.dumps(manga.get(), indent=4))

#chapter = mangas[2].chapter_ids["Chapter"]
#print(scraper.get_chapter(chapter).get())