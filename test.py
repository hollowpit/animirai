from src.sources.mangadex import MangaDex
import json
scraper = MangaDex()
mangas = scraper.popular_manga()
#for manga in mangas:
  #print(json.dumps(manga.get(), indent=4))

chapter = mangas[2].chapter_ids["Chapter 5"]
print(scraper.get_chapter(chapter).get())