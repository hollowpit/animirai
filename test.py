
from src.sources.toonily import Toonily
import os

# Create test_img directory if it doesn't exist
os.makedirs("test_img", exist_ok=True)

# Initialize scraper
scraper = Toonily()

# Search for a manga
print("Searching for manga...")
manga = scraper.search_manga("my landlady")[0].get()
print(f"Found manga: {manga['title']}")

# Get chapter info
chapter_id = manga["chapter_ids"]["Chapter 1"]
print(f"Downloading chapter: {chapter_id}")

# Download the chapter images
scraper.download_chapter(chapter_id)

# Also save chapter info to test.txt for reference
chapter_info = scraper.get_chapter(chapter_id)
with open("test.txt", "w") as test:
    test.write(str(chapter_info.get()))

print("Done! Images saved to test_img directory")
