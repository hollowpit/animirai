
import os
import importlib
import inspect
from src.lib.types import Scraper

def get_all_scrapers():
    """
    Dynamically imports all scraper classes from the sources directory.
    Returns a list of initialized scraper instances.
    """
    scrapers = []
    sources_dir = os.path.join('src', 'sources')
    
    # Check if the sources directory exists
    if not os.path.exists(sources_dir):
        print(f"Error: Sources directory not found at {sources_dir}")
        return scrapers
    
    # Get all Python files in the sources directory
    for filename in os.listdir(sources_dir):
        if filename.endswith('.py') and not filename.startswith('__'):
            module_name = f"src.sources.{filename[:-3]}"
            
            try:
                # Import the module
                module = importlib.import_module(module_name)
                
                # Find all classes in the module that inherit from Scraper
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, Scraper) and 
                        obj is not Scraper):
                        
                        # Create an instance of the scraper
                        scraper_instance = obj()
                        scrapers.append(scraper_instance)
                        print(f"Successfully loaded scraper: {scraper_instance.base_url}")
                        
            except Exception as e:
                print(f"Error importing {module_name}: {e}")
    
    return scrapers

if __name__ == "__main__":
    # Test the function
    all_scrapers = get_all_scrapers()
    print(f"\nTotal scrapers found: {len(all_scrapers)}")
    for i, scraper in enumerate(all_scrapers, 1):
        print(f"{i}. {scraper.__class__.__name__} - {scraper.base_url}")
