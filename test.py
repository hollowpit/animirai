from src.sources.toonily import Toonily
import json
scraper = Toonily()
#print(scraper.search_manga("My Landlady")[0].ge
mangas = scraper.search_manga("My Landlady Noona")
print(json.dumps(mangas[0].get()))
#for manga in mangas: pass
    #print(json.dumps(manga.get(), indent=4))
    #for k, v in manga.get()["chapter_ids"].items():
    #print(json.dumps(scraper.get_chapter("serie/runaway-wife/chapter-22").get(), indent=4))