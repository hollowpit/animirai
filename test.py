
from src.sources.allanime import AllAnime

def test_popular_anime():
    print("=== Testing Popular Anime ===")
    scraper = AllAnime()
    results = scraper.popular_anime(1)
    
    if not results:
        print("No results found for popular anime")
    else:
        print(f"Found {len(results)} popular anime")
        for i, anime in enumerate(results[:3]):  # Print first 3 results
            print(f"Anime {i+1}: {anime.title}")
            print(f"ID: {anime.id}")
            print(f"URL: {anime.url}")
            print(f"Episodes: {anime.episodes}")
            print(f"Poster: {anime.poster}")
            print(anime.episode_ids)
            print(scraper.get_episode(anime.episode_ids["Episode 1"]).get())
            print("-" * 30)

def test_latest_anime():
    print("\n=== Testing Latest Anime ===")
    scraper = AllAnime()
    results = scraper.latest_anime(1)
    
    if not results:
        print("No results found for latest anime")
    else:
        print(f"Found {len(results)} latest anime")
        for i, anime in enumerate(results[:3]):  # Print first 3 results
            print(f"Anime {i+1}: {anime.title}")
            print(f"ID: {anime.id}")
            print(f"URL: {anime.url}")
            print(f"Episodes: {anime.episodes}")
            print(f"Poster: {anime.poster}")
            print("-" * 30)

if __name__ == "__main__":
    test_popular_anime()
    test_latest_anime()
