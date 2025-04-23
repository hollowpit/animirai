from src.sources.hentai3 import Hentai3
import json
scraper = Hentai3()
mangas = scraper.popular_manga()
for manga in mangas:
  print(json.dumps(manga.get(), indent=4))

chapter = mangas[2].chapter_ids["Chapter 1"]
print(scraper.get_chapter(chapter).get())