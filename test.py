from src.sources.toonily import Toonily
scraper = Toonily()
print(scraper.search_manga("my landlady")[0].get())