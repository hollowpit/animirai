from src.sources.toonily import Toonily
scraper = Toonily()
print(scraper.search_manga("My Landlady")[0].get())