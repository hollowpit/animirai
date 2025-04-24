
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import List, Optional
import importlib
import inspect
import os
from src.lib.types import Scraper

app = FastAPI()

def get_all_sources():
    """
    Dynamically imports all scraper classes from the sources directory.
    Returns a list of initialized scraper instances.
    """
    scrapers = []
    sources_dir = os.path.join('src', 'sources')
    
    if not os.path.exists(sources_dir):
        return scrapers
    
    for filename in os.listdir(sources_dir):
        if filename.endswith('.py') and not filename.startswith('__'):
            module_name = f"src.sources.{filename[:-3]}"
            
            try:
                module = importlib.import_module(module_name)
                
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, Scraper) and 
                        obj is not Scraper):
                        
                        scraper_instance = obj()
                        scrapers.append(scraper_instance)
            except Exception as e:
                print(f"Error importing {module_name}: {e}")
    
    return scrapers

sources = get_all_sources()
sources_dict = {scraper.name.lower(): scraper for scraper in sources}

@app.get("/")
async def root():
    return {"message": "Manga Reader API"}

@app.get("/api/sources")
async def get_sources():
    return [{"name": s.name, "url": s.base_url} for s in sources]

@app.get("/api/manga/popular")
async def get_popular_manga(source: str, page: int = 1):
    if source.lower() not in sources_dict:
        raise HTTPException(status_code=404, detail=f"Source '{source}' not found")
    
    scraper = sources_dict[source.lower()]
    try:
        manga_list = scraper.popular_manga(page)
        return [manga.get() for manga in manga_list]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/manga/latest")
async def get_latest_manga(source: str, page: int = 1):
    if source.lower() not in sources_dict:
        raise HTTPException(status_code=404, detail=f"Source '{source}' not found")
    
    scraper = sources_dict[source.lower()]
    try:
        manga_list = scraper.latest_manga(page)
        return [manga.get() for manga in manga_list]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/manga/search")
async def search_manga(source: str, q: str, page: int = 1):
    if source.lower() not in sources_dict:
        raise HTTPException(status_code=404, detail=f"Source '{source}' not found")
    
    scraper = sources_dict[source.lower()]
    try:
        manga_list = scraper.search_manga(q, page)
        return [manga.get() for manga in manga_list]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/manga/chapter")
async def get_chapter(source: str, id: str):
    if source.lower() not in sources_dict:
        raise HTTPException(status_code=404, detail=f"Source '{source}' not found")
    
    scraper = sources_dict[source.lower()]
    try:
        chapter = scraper.get_chapter(id)
        return chapter.get()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
