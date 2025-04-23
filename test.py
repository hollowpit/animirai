from src.sources.toonily import Toonily
import os

# Create scraper instance
scraper = Toonily()

# Search for manga
search_results = scraper.search_manga("my landlady")
if search_results:
    # Get the first manga details
    manga = search_results[0].get()
    print(f"Found manga: {manga.title}")
    
    # Get a chapter
    if manga.chapter_ids:
        chapter_name = list(manga.chapter_ids.keys())[0]  # Get first chapter name
        chapter_id = manga.chapter_ids[chapter_name]
        print(f"Getting chapter: {chapter_name} (ID: {chapter_id})")
        
        # Get chapter and save images
        chapter = scraper.get_chapter(chapter_id)
        print(f"Retrieved chapter with {len(chapter.pages)} pages")
        print(f"Images saved to test_img directory")
    else:
        print("No chapters found for this manga")
else:
    print("No manga found")