
import json
import re
import time
import urllib.parse
import requests
import cloudscraper
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from datetime import datetime
from src.lib.types import Scraper, Manga, Chapter

class Toonily(Scraper):
    def __init__(self):
        super().__init__(
            name="Toonily",
            url="https://toonily.com",
            api_url="https://toonily.com",
            scraper_version="1.0.0"
        )
        self.available_filters = self._get_filters()
        self.available_qualities = []
        self.lang = "en"
        self.session = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False
            }
        )
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Referer": self.base_url,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
            "sec-ch-ua": '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
            "sec-ch-ua-mobile": "?0"
        }
        self.cookies = {
            "toonily-mature": "1"
        }

    def popular_manga_request(self, page: int = 1) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/manga/page/{page}/?m_orderby=trending"
        response = self.session.get(
            url, 
            headers=self.headers,
            cookies=self.cookies,
            timeout=30
        )
        if response.status_code != 200:
            return []
        
        soup = BeautifulSoup(response.text, "html.parser")
        return self._parse_manga_list(soup)

    def popular_manga(self, page: int = 1) -> List[Manga]:
        manga_list = self.popular_manga_request(page)
        return [self._convert_to_manga(manga) for manga in manga_list]

    def latest_manga_request(self, page: int = 1) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/manga/page/{page}/?m_orderby=latest"
        response = self.session.get(
            url, 
            headers=self.headers,
            cookies=self.cookies,
            timeout=30
        )
        if response.status_code != 200:
            return []
        
        soup = BeautifulSoup(response.text, "html.parser")
        return self._parse_manga_list(soup)

    def latest_manga(self, page: int = 1) -> List[Manga]:
        manga_list = self.latest_manga_request(page)
        return [self._convert_to_manga(manga) for manga in manga_list]

    def search_manga_request(self, query: str, page: int = 1, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        filters = filters or {}
        
        if query.startswith("id:"):
            manga_id = query[3:]
            manga_details = self.manga_details_request(manga_id)
            return [manga_details] if manga_details else []
        
        url = f"{self.base_url}/?s={urllib.parse.quote(query)}&post_type=wp-manga"
        if page > 1:
            url += f"&paged={page}"
        
        if filters:
            if "genres" in filters:
                genres = filters["genres"].split(",")
                for genre in genres:
                    url += f"&genre[]={urllib.parse.quote(genre.strip())}"
            
            if "status" in filters:
                url += f"&status={urllib.parse.quote(filters['status'])}"
                
            if "orderby" in filters:
                url += f"&m_orderby={urllib.parse.quote(filters['orderby'])}"
                
        response = self.session.get(
            url, 
            headers=self.headers,
            cookies=self.cookies,
            timeout=30
        )
        if response.status_code != 200:
            return []
        
        soup = BeautifulSoup(response.text, "html.parser")
        return self._parse_manga_list(soup)

    def search_manga(self, query: str, page: int = 1, filters: Optional[Dict[str, Any]] = None) -> List[Manga]:
        manga_list = self.search_manga_request(query, page, filters)
        return [self._convert_to_manga(manga) for manga in manga_list]

    def manga_details_request(self, manga_id: str) -> Dict[str, Any]:
        if manga_id.isdigit():
            url = f"{self.base_url}/manga?p={manga_id}"
        else:
            url = f"{self.base_url}/serie/{manga_id}"
        
        response = self.session.get(
            url, 
            headers=self.headers,
            cookies=self.cookies,
            timeout=30
        )
        if response.status_code != 200:
            return {}
        
        soup = BeautifulSoup(response.text, "html.parser")
        return self._parse_manga_details(soup, manga_id)

    def get_chapter(self, chapter_id: str) -> Chapter:
        url = f"{self.base_url}/{chapter_id}"
        response = self.session.get(
            url, 
            headers=self.headers,
            cookies=self.cookies,
            timeout=30
        )
        if response.status_code != 200:
            return Chapter(
                title="Error loading chapter",
                pages=[],
                id=chapter_id
            )
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Get chapter title
        title_element = soup.select_one(".c-breadcrumb .breadcrumb li:last-child")
        title = title_element.text.strip() if title_element else "Chapter"
        
        # Get pages
        pages = []
        containers = soup.select(".reading-content .page-break")
        for container in containers:
            img_element = container.select_one("img")
            if img_element:
                img_url = img_element.get("data-src") or img_element.get("src")
                if img_url:
                    # Fix relative URLs
                    if img_url.startswith("/"):
                        img_url = f"{self.base_url}{img_url}"
                    pages.append(img_url)
        
        return Chapter(
            title=title,
            pages=pages,
            id=chapter_id
        )

    def _convert_to_manga(self, manga_dict: Dict[str, Any]) -> Manga:
        if not manga_dict:
            return None

        manga_id = manga_dict.get("id", "")
        title = manga_dict.get("title", "Unknown")
        author = manga_dict.get("author", "Unknown")
        description = manga_dict.get("description", "")
        poster = manga_dict.get("thumbnail_url", "")
        status = manga_dict.get("status", "Ongoing")
        genres = manga_dict.get("genres", [])

        # Get chapter IDs
        chapter_ids = {}
        for chapter in manga_dict.get("chapters", []):
            chapter_ids[chapter.get("title", "Chapter")] = chapter.get("id", "")

        return Manga(
            id=manga_id,
            url=manga_dict.get("url", ""),
            title=title,
            author=author,
            description=description,
            poster=poster,
            chapters=len(chapter_ids),
            chapter_ids=chapter_ids,
            tags=genres,
            genres=genres,
            status=status
        )

    def _parse_manga_list(self, soup) -> List[Dict[str, Any]]:
        manga_list = []
        manga_elements = soup.select(".c-tabs-item .row.c-tabs-item__content")
        
        for element in manga_elements:
            try:
                link_element = element.select_one(".tab-thumb a")
                if not link_element:
                    continue
                
                url = link_element.get("href", "")
                if not url:
                    continue
                
                # Get ID from URL
                manga_id = url.split("/")[-2] if url.endswith("/") else url.split("/")[-1]
                
                # Get title
                title_element = element.select_one(".post-title h3 a")
                title = title_element.text.strip() if title_element else "Unknown"
                
                # Get thumbnail
                thumbnail_element = link_element.select_one("img")
                thumbnail_url = thumbnail_element.get("data-src") or thumbnail_element.get("src") if thumbnail_element else ""
                
                # Remove thumbnail size suffix to get higher quality
                if thumbnail_url:
                    thumbnail_url = re.sub(r'-\d+x\d+(\.\w+)$', r'\1', thumbnail_url)
                
                # Get description (not available in list view)
                description = ""
                
                # Get genres
                genre_elements = element.select(".mg_genres .mg_genre")
                genres = [g.text.strip() for g in genre_elements]
                
                # Get rating
                rating_element = element.select_one(".score")
                rating = float(rating_element.text.strip()) if rating_element else 0.0
                
                # Get status
                status_element = element.select_one(".mg_status")
                status = status_element.text.strip() if status_element else "Ongoing"
                
                # Get chapters
                chapters = []
                latest_chapters = element.select(".chapter-item .chapter a")
                for chapter in latest_chapters:
                    chapter_url = chapter.get("href", "")
                    chapter_id = chapter_url.split("/")[-2] if chapter_url.endswith("/") else chapter_url.split("/")[-1]
                    chapter_title = chapter.text.strip()
                    chapters.append({
                        "id": chapter_id,
                        "title": chapter_title,
                        "url": chapter_url
                    })
                
                manga_list.append({
                    "id": manga_id,
                    "title": title,
                    "url": url,
                    "thumbnail_url": thumbnail_url,
                    "description": description,
                    "genres": genres,
                    "status": status,
                    "rating": rating,
                    "chapters": chapters
                })
            except Exception:
                continue
        
        return manga_list

    def _parse_manga_details(self, soup, manga_id: str) -> Dict[str, Any]:
        try:
            # Get title
            title_element = soup.select_one(".post-title h1")
            title = title_element.text.strip() if title_element else "Unknown"
            
            # Get URL
            url = soup.select_one('link[rel="canonical"]')
            url = url.get("href", "") if url else ""
            
            # Get thumbnail
            thumbnail_element = soup.select_one(".summary_image img")
            thumbnail_url = thumbnail_element.get("data-src") or thumbnail_element.get("src") if thumbnail_element else ""
            
            # Remove thumbnail size suffix to get higher quality
            if thumbnail_url:
                thumbnail_url = re.sub(r'-\d+x\d+(\.\w+)$', r'\1', thumbnail_url)
            
            # Get description
            description_element = soup.select_one(".summary__content .description-summary")
            description = description_element.text.strip() if description_element else ""
            
            # Get genres
            genre_elements = soup.select(".genres-content a")
            genres = [g.text.strip() for g in genre_elements]
            
            # Get author
            author_elements = soup.select(".author-content a")
            author = ", ".join([a.text.strip() for a in author_elements]) if author_elements else "Unknown"
            
            # Get status
            status_element = soup.select_one(".post-status .summary-content")
            status = status_element.text.strip() if status_element else "Ongoing"
            
            # Get chapters
            chapters = []
            chapter_elements = soup.select(".wp-manga-chapter")
            for chapter in chapter_elements:
                link = chapter.select_one("a")
                if not link:
                    continue
                
                chapter_url = link.get("href", "")
                chapter_id = chapter_url.split("/")[-2] if chapter_url.endswith("/") else chapter_url.split("/")[-1]
                chapter_title = link.text.strip()
                
                # Get release date if available
                date_element = chapter.select_one(".chapter-release-date")
                release_date = date_element.text.strip() if date_element else ""
                
                chapters.append({
                    "id": chapter_id,
                    "title": chapter_title,
                    "url": chapter_url,
                    "release_date": release_date
                })
            
            return {
                "id": manga_id,
                "title": title,
                "url": url,
                "thumbnail_url": thumbnail_url,
                "description": description,
                "genres": genres,
                "author": author,
                "status": status,
                "chapters": chapters
            }
        except Exception:
            return {
                "id": manga_id,
                "title": "Unknown",
                "url": f"{self.base_url}/serie/{manga_id}",
                "thumbnail_url": "",
                "description": "",
                "genres": [],
                "author": "Unknown",
                "status": "Unknown",
                "chapters": []
            }

    def _get_filters(self) -> Dict[str, Any]:
        return {
            "orderby": [
                {"name": "Default", "value": ""},
                {"name": "A-Z", "value": "title"},
                {"name": "Latest", "value": "latest"},
                {"name": "Rating", "value": "rating"},
                {"name": "Trending", "value": "trending"},
                {"name": "Most Views", "value": "views"},
                {"name": "New", "value": "new-manga"}
            ],
            "status": [
                {"name": "All", "value": ""},
                {"name": "Ongoing", "value": "ongoing"},
                {"name": "Completed", "value": "completed"},
                {"name": "Hiatus", "value": "hiatus"},
                {"name": "Canceled", "value": "canceled"}
            ],
            "genres": [
                "Action", "Adult", "Adventure", "Comedy", "Completed", "Drama", 
                "Ecchi", "Fantasy", "Harem", "Josei", "Mature", "Mystery", 
                "Psychological", "Romance", "School Life", "Sci-fi", "Seinen", 
                "Shoujo", "Shounen", "Slice of Life", "Smut", "Supernatural", 
                "Tragedy", "Yaoi", "Yuri"
            ]
        }
