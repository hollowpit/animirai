from src.sources.allanime import AllAnime
scraper = AllAnime()
results = scraper.popular_anime("")
print(results)