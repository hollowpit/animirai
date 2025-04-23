from src.sources.comickio import Comick
import json
import time

# Initialize scraper
scraper = Comick()

# Get latest manga
print("Getting latest manga...")
mangas = scraper.latest_manga()
print(f"Got {len(mangas)} manga")
print(mangas[99].get())

# Get details for a manga
print("\nGetting manga details...")
start_time = time.time()
manga = scraper.manga_details(mangas[5].id)
end_time = time.time()
print(f"Manga details fetched in {end_time - start_time:.2f} seconds")
print(json.dumps(manga.get(), indent=4))

# Get a chapter using the first chapter ID
print("\nGetting first chapter...")
chapter_ids = manga.chapter_ids
first_chapter_title = list(chapter_ids.keys())[0]
first_chapter_id = chapter_ids[first_chapter_title]
print(f"Getting chapter: {first_chapter_title} (ID: {first_chapter_id})")

start_time = time.time()
chapter = scraper.get_chapter(first_chapter_id)
end_time = time.time()
print(f"Chapter fetched in {end_time - start_time:.2f} seconds")
print(json.dumps(chapter.get(), indent=4))