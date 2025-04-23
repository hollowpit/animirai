
import json
import cloudscraper
import requests
import time
import re
from typing import List, Dict, Any
from datetime import datetime
from src.lib.types import Scraper, Manga, Chapter

class MangaDex(Scraper):
    def __init__(self):
        super().__init__("MangaDex", "https://mangadex.org", api_url="https://api.mangadex.org", scraper_version="1.0.0")
        self.session = cloudscraper.create_scraper()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": self.base_url,
            "Origin": self.base_url,
        }
        self.cdn_url = "https://uploads.mangadex.org"
        self.lang = "en"
        self.available_filters = {
            "content_rating": ["safe", "suggestive", "erotica", "pornographic"],
            "order": ["relevance", "latestUploadedChapter", "title", "rating", "followedCount"],
            "status": ["ongoing", "completed", "hiatus", "cancelled"],
            "publication_demographic": ["none", "shounen", "shoujo", "seinen", "josei"]
        }

    def search_manga(self, query: str, page: int = 1) -> List[Manga]:
        offset = (page - 1) * 12
        params = {
            "title": query,
            "limit": 12,
            "offset": offset,
            "includes[]": "cover_art",
            "contentRating[]": ["safe", "suggestive", "erotica"],
            "availableTranslatedLanguage[]": self.lang
        }
        
        url = f"{self.api_url}/manga"
        response = self.session.get(url, params=params, headers=self.headers)
        
        if response.status_code != 200:
            return []
            
        data = response.json()
        return self._parse_manga_list(data)
        
    def _parse_manga_list(self, data: Dict[str, Any]) -> List[Manga]:
        manga_list = []
        
        for manga_data in data.get("data", []):
            manga_id = manga_data.get("id")
            attributes = manga_data.get("attributes", {})
            
            title = attributes.get("title", {}).get(self.lang)
            if not title:
                title = attributes.get("title", {}).get("en")
            if not title:
                titles = list(attributes.get("title", {}).values())
                title = titles[0] if titles else "Unknown Title"
                
            description = attributes.get("description", {}).get(self.lang)
            if not description:
                description = attributes.get("description", {}).get("en", "No description available.")
            
            cover_file = None
            for relationship in manga_data.get("relationships", []):
                if relationship.get("type") == "cover_art":
                    cover_file = relationship.get("attributes", {}).get("fileName")
                    
            cover_url = f"{self.cdn_url}/covers/{manga_id}/{cover_file}" if cover_file else None
            
            # Get available chapters
            chapters = {}
            try:
                aggregate_url = f"{self.api_url}/manga/{manga_id}/aggregate?translatedLanguage[]={self.lang}"
                agg_response = self.session.get(aggregate_url, headers=self.headers)
                if agg_response.status_code == 200:
                    agg_data = agg_response.json()
                    for volume_key, volume in agg_data.get("volumes", {}).items():
                        for chapter_key, chapter in volume.get("chapters", {}).items():
                            chapter_id = chapter.get("id")
                            chapter_num = chapter_key if chapter_key != "none" else "1"
                            chapters[f"Chapter {chapter_num}"] = chapter_id
            except:
                pass
                
            manga_list.append(
                Manga(
                    id=manga_id,
                    url=f"/manga/{manga_id}",
                    title=title,
                    author=self._get_creator(manga_data, "author"),
                    description=description,
                    poster=cover_url,
                    chapters=len(chapters) if chapters else 0,
                    tags=self._get_tags(attributes),
                    genres=self._get_genres(attributes),
                    status=attributes.get("status", "ongoing"),
                    rating=attributes.get("rating", {}).get("bayesian", 0.0),
                    chapter_ids=chapters
                )
            )
            
        return manga_list
        
    def _get_creator(self, manga_data: Dict[str, Any], creator_type: str) -> str:
        creators = []
        for relationship in manga_data.get("relationships", []):
            if relationship.get("type") == creator_type:
                name = relationship.get("attributes", {}).get("name")
                if name:
                    creators.append(name)
        return ", ".join(creators)
        
    def _get_tags(self, attributes: Dict[str, Any]) -> List[str]:
        tags = []
        for tag in attributes.get("tags", []):
            if tag.get("attributes", {}).get("group") != "genre":
                name = tag.get("attributes", {}).get("name", {}).get(self.lang)
                if not name:
                    name = tag.get("attributes", {}).get("name", {}).get("en")
                if name:
                    tags.append(name)
        return tags
        
    def _get_genres(self, attributes: Dict[str, Any]) -> List[str]:
        genres = []
        for tag in attributes.get("tags", []):
            if tag.get("attributes", {}).get("group") == "genre":
                name = tag.get("attributes", {}).get("name", {}).get(self.lang)
                if not name:
                    name = tag.get("attributes", {}).get("name", {}).get("en")
                if name:
                    genres.append(name)
        return genres
        
    def latest_manga(self, page: int = 1) -> List[Manga]:
        offset = (page - 1) * 12
        params = {
            "limit": 12,
            "offset": offset,
            "includes[]": "cover_art",
            "contentRating[]": ["safe", "suggestive", "erotica"],
            "order[latestUploadedChapter]": "desc",
            "availableTranslatedLanguage[]": self.lang
        }
        
        url = f"{self.api_url}/manga"
        response = self.session.get(url, params=params, headers=self.headers)
        
        if response.status_code != 200:
            return []
            
        data = response.json()
        return self._parse_manga_list(data)
        
    def popular_manga(self, page: int = 1) -> List[Manga]:
        offset = (page - 1) * 12
        params = {
            "limit": 12,
            "offset": offset,
            "includes[]": "cover_art",
            "contentRating[]": ["safe", "suggestive", "erotica"],
            "order[followedCount]": "desc",
            "availableTranslatedLanguage[]": self.lang
        }
        
        url = f"{self.api_url}/manga"
        response = self.session.get(url, params=params, headers=self.headers)
        
        if response.status_code != 200:
            return []
            
        data = response.json()
        return self._parse_manga_list(data)
        
    def get_manga(self, manga_id: str) -> Manga:
        url = f"{self.api_url}/manga/{manga_id}?includes[]=cover_art&includes[]=author&includes[]=artist"
        response = self.session.get(url, headers=self.headers)
        
        if response.status_code != 200:
            return None
            
        data = response.json()
        manga_list = self._parse_manga_list(data)
        return manga_list[0] if manga_list else None
        
    def get_chapter(self, chapter_id: str) -> Chapter:
        url = f"{self.api_url}/chapter/{chapter_id}"
        response = self.session.get(url, headers=self.headers)
        
        if response.status_code != 200:
            return None
            
        chapter_data = response.json().get("data", {})
        attributes = chapter_data.get("attributes", {})
        
        # Get chapter title
        volume = attributes.get("volume")
        chapter_num = attributes.get("chapter")
        title = attributes.get("title")
        
        chapter_title = []
        if volume:
            chapter_title.append(f"Vol.{volume}")
        if chapter_num:
            chapter_title.append(f"Ch.{chapter_num}")
        if title:
            if chapter_title:
                chapter_title.append("-")
            chapter_title.append(title)
            
        if not chapter_title:
            chapter_title = ["Oneshot"]
            
        # Get pages
        at_home_url = f"{self.api_url}/at-home/server/{chapter_id}"
        at_home_response = self.session.get(at_home_url, headers=self.headers)
        
        pages = []
        if at_home_response.status_code == 200:
            at_home_data = at_home_response.json()
            server = at_home_data.get("baseUrl")
            chapter_hash = at_home_data.get("chapter", {}).get("hash")
            
            # Prefer data-saver for bandwidth optimization
            page_filenames = at_home_data.get("chapter", {}).get("dataSaver", [])
            page_type = "data-saver"
            
            if not page_filenames:
                page_filenames = at_home_data.get("chapter", {}).get("data", [])
                page_type = "data"
                
            for filename in page_filenames:
                pages.append(f"{server}/{page_type}/{chapter_hash}/{filename}")
                
        return Chapter(
            title=" ".join(chapter_title),
            pages=pages,
            id=chapter_id
        )
