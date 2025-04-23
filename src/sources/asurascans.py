
import json
import re
import time
import requests
import cloudscraper
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from datetime import datetime
from src.lib.types import Scraper, Manga, Chapter

class AsuraScans(Scraper):
    def __init__(self):
        super().__init__(
            name="AsuraScans",
            url="https://asuracomic.net",
            api_url="https://gg.asuracomic.net/api",
            scraper_version="1.0.0"
        )
        self.session = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False
            }
        )
        self.headers = {
            "Referer": f"{self.base_url}/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": self.base_url,
            "Connection": "keep-alive"
        }
        self.available_filters = self._get_filters()

    def popular_manga(self, page: int = 1) -> List[Manga]:
        url = f"{self.base_url}/series?genres=&status=-1&types=-1&order=rating&page={page}"
        response = self.session.get(url, headers=self.headers)
        if response.status_code != 200:
            return []
        
        soup = BeautifulSoup(response.text, "html.parser")
        return self._parse_manga_list(soup)

    def latest_manga(self, page: int = 1) -> List[Manga]:
        url = f"{self.base_url}/series?genres=&status=-1&types=-1&order=update&page={page}"
        response = self.session.get(url, headers=self.headers)
        if response.status_code != 200:
            return []
        
        soup = BeautifulSoup(response.text, "html.parser")
        return self._parse_manga_list(soup)

    def search_manga(self, query: str, page: int = 1, filters: Optional[Dict[str, Any]] = None) -> List[Manga]:
        filters = filters or {}
        url = f"{self.base_url}/series"
        params = {"page": page}
        
        if query:
            params["name"] = query
        
        genres = []
        if "genres" in filters:
            genres = filters["genres"].split(",")
        
        status = filters.get("status", "-1")
        types = filters.get("types", "-1")
        order = filters.get("order", "rating")
        
        params["genres"] = ",".join(genres)
        params["status"] = status
        params["types"] = types
        params["order"] = order
        
        response = self.session.get(url, params=params, headers=self.headers)
        if response.status_code != 200:
            return []
        
        soup = BeautifulSoup(response.text, "html.parser")
        return self._parse_manga_list(soup)

    def get_manga(self, manga_id: str) -> Manga:
        url = f"{self.base_url}/series/{manga_id}"
        response = self.session.get(url, headers=self.headers)
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.text, "html.parser")
        manga_details = self._extract_manga_details(soup, manga_id)
        
        chapters_data = self._get_chapters(soup, manga_id)
        chapter_ids = {}
        for chapter in chapters_data:
            chapter_ids[chapter["name"]] = chapter["id"]
        
        manga_details["chapter_ids"] = chapter_ids
        manga_details["chapters"] = len(chapter_ids)
        
        return Manga(
            id=manga_details["id"],
            url=manga_details["url"],
            title=manga_details["title"],
            author=manga_details["author"],
            description=manga_details["description"],
            poster=manga_details["thumbnail_url"],
            chapters=manga_details["chapters"],
            tags=manga_details["genres"],
            genres=manga_details["genres"],
            status=manga_details["status"],
            chapter_ids=chapter_ids
        )

    def get_chapter(self, chapter_id: str) -> Chapter:
        url = f"{self.base_url}/chapter/{chapter_id}"
        response = self.session.get(url, headers=self.headers)
        if response.status_code != 200:
            return Chapter(title="Error loading chapter", pages=[], id=chapter_id)
        
        soup = BeautifulSoup(response.text, "html.parser")
        script_data = soup.select("script:contains(self.__next_f.push)")
        
        script_content = ""
        for script in script_data:
            script_content += script.string or ""
        
        pages_match = re.search(r'"pages":(\[.*?\])', script_content)
        if not pages_match:
            return Chapter(title="No pages found", pages=[], id=chapter_id)
        
        pages_json = pages_match.group(1).replace('\\"', '"')
        try:
            pages_data = json.loads(pages_json)
            pages = [page["url"] for page in sorted(pages_data, key=lambda x: x.get("order", 0))]
            
            title_element = soup.select_one("h1.flex-1, h2.flex-1")
            title = title_element.text.strip() if title_element else f"Chapter {chapter_id}"
            
            return Chapter(title=title, pages=pages, id=chapter_id)
        except Exception as e:
            return Chapter(title="Error parsing chapter data", pages=[], id=chapter_id)

    def _parse_manga_list(self, soup) -> List[Manga]:
        manga_elements = soup.select("div.grid > a[href]")
        manga_list = []
        
        for element in manga_elements:
            title_element = element.select_one("div.block > span.block")
            if not title_element:
                continue
                
            title = title_element.text.strip()
            url = element.get("href", "")
            manga_id = url.split("/")[-1] if url else ""
            
            thumbnail_element = element.select_one("img")
            thumbnail_url = thumbnail_element.get("src", "") if thumbnail_element else ""
            if thumbnail_url and not thumbnail_url.startswith("http"):
                thumbnail_url = self.base_url + thumbnail_url
            
            manga = Manga(
                id=manga_id,
                url=f"/series/{manga_id}",
                title=title,
                author="Unknown",
                description="",
                poster=thumbnail_url,
                chapters=0,
                chapter_ids={}
            )
            
            manga_list.append(manga)
        
        return manga_list

    def _extract_manga_details(self, soup, manga_id: str) -> Dict[str, Any]:
        title_element = soup.select_one("span.text-xl.font-bold, h3.truncate")
        title = title_element.text.strip() if title_element else f"Manga #{manga_id}"
        
        thumbnail_element = soup.select_one("img[alt=poster]")
        thumbnail_url = thumbnail_element.get("src", "") if thumbnail_element else ""
        if thumbnail_url and not thumbnail_url.startswith("http"):
            thumbnail_url = self.base_url + thumbnail_url
        
        description_element = soup.select_one("span.font-medium.text-sm")
        description = description_element.text.strip() if description_element else ""
        
        author_element = soup.select_one("div.grid > div:has(h3:contains(Author)) > h3:nth-of-type(2)")
        author = author_element.text.strip() if author_element else "Unknown"
        
        artist_element = soup.select_one("div.grid > div:has(h3:contains(Artist)) > h3:nth-of-type(2)")
        artist = artist_element.text.strip() if artist_element else "Unknown"
        
        genres = []
        type_element = soup.select_one("div.flex:has(h3:contains(type)) > h3:nth-of-type(2)")
        if type_element:
            genres.append(type_element.text.strip())
        
        genre_elements = soup.select("div[class^=space] > div.flex > button.text-white")
        for genre in genre_elements:
            genres.append(genre.text.strip())
        
        status_element = soup.select_one("div.flex:has(h3:contains(Status)) > h3:nth-of-type(2)")
        status_text = status_element.text.strip() if status_element else "Unknown"
        
        status = "Ongoing"
        if status_text == "Completed":
            status = "Completed"
        elif status_text == "Hiatus":
            status = "Hiatus"
        elif status_text in ["Dropped", "Cancelled"]:
            status = "Cancelled"
        
        return {
            "id": manga_id,
            "url": f"/series/{manga_id}",
            "title": title,
            "author": author,
            "artist": artist,
            "description": description,
            "thumbnail_url": thumbnail_url,
            "genres": genres,
            "status": status
        }

    def _get_chapters(self, soup, manga_id: str) -> List[Dict[str, Any]]:
        chapters = []
        chapter_elements = soup.select("div.scrollbar-thumb-themecolor > div.group")
        
        for element in chapter_elements:
            chapter_link = element.select_one("a")
            if not chapter_link:
                continue
                
            chapter_url = chapter_link.get("href", "")
            chapter_id = chapter_url.split("/")[-1] if chapter_url else ""
            
            chapter_number_element = element.select_one("h3")
            chapter_number = chapter_number_element.text.strip() if chapter_number_element else ""
            
            chapter_title_elements = element.select("h3 > span")
            chapter_title = " ".join([span.text.strip() for span in chapter_title_elements])
            
            name = chapter_number
            if chapter_title:
                name = f"{chapter_number} - {chapter_title}"
            
            date_element = element.select_one("h3 + h3")
            date_text = date_element.text.strip() if date_element else ""
            date_upload = 0
            
            if date_text:
                try:
                    date_text = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_text)
                    date_format = "%B %d %Y"
                    date_obj = datetime.strptime(date_text, date_format)
                    date_upload = int(date_obj.timestamp() * 1000)
                except Exception:
                    date_upload = 0
            
            chapters.append({
                "id": chapter_id,
                "url": chapter_url,
                "name": name,
                "uploaded": date_upload
            })
        
        return chapters

    def _get_filters(self) -> Dict[str, Any]:
        try:
            response = self.session.get(f"{self.api_url}/series/filters", headers=self.headers)
            if response.status_code != 200:
                return self._get_default_filters()
            
            filters = response.json()
            genres = [(genre["name"].strip(), genre["id"]) for genre in filters.get("genres", []) if genre.get("id", 0) > 0]
            statuses = [(status["name"].strip(), status["id"]) for status in filters.get("statuses", [])]
            types = [(type_item["name"].strip(), type_item["id"]) for type_item in filters.get("types", [])]
            
            return {
                "genres": genres,
                "statuses": statuses,
                "types": types,
                "orders": [
                    ("Rating", "rating"),
                    ("Update", "update"),
                    ("Latest", "latest"),
                    ("Z-A", "desc"),
                    ("A-Z", "asc"),
                ]
            }
        except Exception:
            return self._get_default_filters()

    def _get_default_filters(self) -> Dict[str, Any]:
        return {
            "genres": [],
            "statuses": [
                ("All", "-1"),
                ("Ongoing", "1"),
                ("Completed", "2"),
                ("Hiatus", "3"),
                ("Dropped", "4")
            ],
            "types": [
                ("All", "-1"),
                ("Manga", "1"),
                ("Manhwa", "2"),
                ("Manhua", "3"),
                ("Comic", "4")
            ],
            "orders": [
                ("Rating", "rating"),
                ("Update", "update"),
                ("Latest", "latest"),
                ("Z-A", "desc"),
                ("A-Z", "asc"),
            ]
        }
