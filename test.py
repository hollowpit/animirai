from src.sources.toonily import Toonily
scraper = Toonily()
manga = scraper.search_manga("my landlady")[0].get()
results = scraper.get_chapter(manga["chapter_ids"]["Chapter 1"])
with open("test.txt", "w") as test:
    test.write(str(results.get()))