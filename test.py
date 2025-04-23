
import sys

#from src.sources.toonily import Toonily
from src.sources.hentairead import HentaiRead
Toonily="n&"
def test_toonily():
    print("Testing Toonily scraper...")
    
    scraper = Toonily()
    
    print("\nTesting popular manga:")
    mangas = scraper.popular_manga()
    if not mangas:
        print("No popular manga found!")
    else:
        print(f"Found {len(mangas)} popular manga")
        for manga in mangas[:3]:  # Print first 3 only
            print(f"- {manga.title}")
    
    print("\nTesting latest manga:")
    latest = scraper.latest_manga()
    if not latest:
        print("No latest manga found!")
    else:
        print(f"Found {len(latest)} latest manga")
        for manga in latest[:3]:  # Print first 3 only
            print(f"- {manga.title}")
    
    print("\nTesting search manga:")
    query = "solo"
    search = scraper.search_manga(query)
    if not search:
        print(f"No manga found for query: {query}")
    else:
        print(f"Found {len(search)} manga for query: {query}")
        for manga in search[:3]:  # Print first 3 only
            print(f"- {manga.title}")
    
    # If we have a manga, test details
    if mangas:
        print("\nTesting manga details:")
        manga_id = mangas[0].id
        details = scraper.manga_details(manga_id)
        if details:
            print(f"Title: {details.title}")
            print(f"Author: {details.author}")
            print(f"Chapters: {details.chapters}")
            print(f"Genres: {', '.join(details.genres[:5]) if details.genres else 'None'}")
            
            # If we have chapters, test one
            if details.chapter_ids:
                print("\nTesting chapter retrieval:")
                chapter_id = next(iter(details.chapter_ids.values()))
                chapter = scraper.get_chapter(chapter_id)
                if chapter:
                    print(f"Chapter title: {chapter.title}")
                    print(f"Number of pages: {chapter.total_pages}")
                else:
                    print("Failed to retrieve chapter")
        else:
            print("Failed to retrieve manga details")

def test_hentairead():
    print("Testing HentaiRead scraper...")
    
    scraper = HentaiRead()
    
    print("\nTesting popular manga:")
    mangas = scraper.popular_manga()
    if not mangas:
        print("No popular manga found!")
    else:
        print(f"Found {len(mangas)} popular manga")
        for manga in mangas[:3]:  # Print first 3 only
            print(f"- {manga.title}")
    
    print("\nTesting latest manga:")
    latest = scraper.latest_manga()
    if not latest:
        print("No latest manga found!")
    else:
        print(f"Found {len(latest)} latest manga")
        for manga in latest[:3]:  # Print first 3 only
            print(f"- {manga.title}")
    
    print("\nTesting search manga:")
    query = "demon"
    search = scraper.search_manga(query)
    if not search:
        print(f"No manga found for query: {query}")
    else:
        print(f"Found {len(search)} manga for query: {query}")
        for manga in search[:3]:  # Print first 3 only
            print(f"- {manga.title}")
    
    # If we have a manga, test details
    if mangas:
        print("\nTesting manga details:")
        manga_id = mangas[0].id
        print(manga_id)
        details = scraper.manga_details(manga_id)
        if details:
            print(f"Title: {details.title}")
            print(f"Author: {details.author}")
            print(f"Genres: {', '.join(details.genres[:5]) if details.genres else 'None'}")
            
            # If we have chapters, test on
            if details.chapter_ids:
                print("\nTesting chapter retrieval:")
                print(details.chapter_ids)
                chapter_id = next(iter(details.chapter_ids.values()))
                print(chapter_id)
                chapter = scraper.get_chapter(chapter_id)
                if chapter:
                    print(f"Chapter title: {chapter.title}")
                    print(f"Number of pages: {chapter.total_pages}")
                else:
                    print("Failed to retrieve chapter")
        else:
            print("Failed to retrieve manga details")

if __name__ == "__main__":
    #test_toonily()
    # Uncomment to test HentaiRead
    test_hentairead()
