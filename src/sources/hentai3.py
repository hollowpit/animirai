
import json
import re
import time
import urllib.parse
import requests
import cloudscraper
from typing import List, Dict, Any, Optional
from datetime import datetime
from src.lib.types import Scraper, Manga, Chapter

class Hentai3(Scraper):
    def __init__(self):
        super().__init__(
            name="3Hentai",
            url="https://3hentai.net",
            api_url="https://3hentai.net",
            scraper_version="1.0.0"
        )
        self.available_filters = self._get_filters()
        self.available_qualities = []
        self.lang = "all"
        self.session = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False
            }
        )
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Referer": f"{self.base_url}/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": self.base_url,
            "Connection": "keep-alive",
            "sec-ch-ua": '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
            "sec-ch-ua-mobile": "?0"
        }
        self.date_format = "%Y-%m-%dT%H:%M:%S%z"

    def popular_manga_request(self, page: int = 1) -> List[Dict[str, Any]]:
        search_lang = ""
        if search_lang:
            url = f"{self.base_url}/language/{search_lang}/{page if page > 1 else ''}?sort=popular"
        else:
            url = f"{self.base_url}/search?q=pages%3A>0&pages={page}&sort=popular"
        
        response = self.session.get(url, headers=self.headers)
        if response.status_code != 200:
            return []
        
        soup = self._parse_response(response.text)
        return self._extract_manga_list(soup)

    def popular_manga(self, page: int = 1) -> List[Manga]:
        manga_list = self.popular_manga_request(page)
        return [self._convert_to_manga(manga) for manga in manga_list]

    def latest_manga_request(self, page: int = 1) -> List[Dict[str, Any]]:
        search_lang = ""
        if search_lang:
            url = f"{self.base_url}/language/{search_lang}/{page}"
        else:
            url = f"{self.base_url}/search?q=pages%3A>0&pages={page}"
        
        response = self.session.get(url, headers=self.headers)
        if response.status_code != 200:
            return []
        
        soup = self._parse_response(response.text)
        return self._extract_manga_list(soup)

    def latest_manga(self, page: int = 1) -> List[Manga]:
        manga_list = self.latest_manga_request(page)
        return [self._convert_to_manga(manga) for manga in manga_list]

    def search_manga_request(self, query: str, page: int = 1, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        filters = filters or {}
        search_lang = ""
        tags = []
        
        if search_lang:
            tags.append(f"language:{search_lang}")
        
        single_tag = None
        sort = ""
        
        if filters:
            if "sort" in filters:
                sort = filters["sort"]
            
            tag_types = ["tags", "male_tags", "female_tags", "series", "characters", "artist", "groups", "language", "page"]
            for tag_type in tag_types:
                if tag_type in filters and filters[tag_type]:
                    if tag_type == "male_tags":
                        tag_values = filters[tag_type].split(",")
                        for tag in tag_values:
                            trimmed = tag.strip().lower()
                            prefix = "-" if trimmed.startswith('-') else ""
                            cleaned_tag = trimmed.removeprefix("-")
                            tags.append(f"{prefix}tags:'{cleaned_tag} (male)'")
                    elif tag_type == "female_tags":
                        tag_values = filters[tag_type].split(",")
                        for tag in tag_values:
                            trimmed = tag.strip().lower()
                            prefix = "-" if trimmed.startswith('-') else ""
                            cleaned_tag = trimmed.removeprefix("-")
                            tags.append(f"{prefix}tags:'{cleaned_tag} (female)'")
                    else:
                        tag_values = filters[tag_type].split(",")
                        if len(tag_values) < 2 and tag_type != "tags":
                            single_tag = (tag_type, filters[tag_type].replace(" ", "-"))
                        else:
                            for tag in tag_values:
                                trimmed = tag.strip().lower()
                                prefix = "-" if trimmed.startswith('-') else ""
                                cleaned_tag = trimmed.removeprefix("-")
                                tags.append(f"{prefix}{tag_type}:'{cleaned_tag}'")
        
        if single_tag:
            url = f"{self.base_url}/{single_tag[0]}/{single_tag[1]}"
            if page > 1:
                url += f"/{page}"
            if sort:
                url += f"?sort={sort}"
        else:
            url = f"{self.base_url}/search"
            q_param = ""
            if tags:
                q_param = ",".join(tags)
            elif query:
                q_param = query
            else:
                q_param = "page:>0"
            
            url += f"?q={urllib.parse.quote(q_param)}"
            if page > 1:
                url += f"&page={page}"
            if sort:
                url += f"&sort={sort}"
        
        response = self.session.get(url, headers=self.headers)
        if response.status_code != 200:
            return []
        
        soup = self._parse_response(response.text)
        return self._extract_manga_list(soup)

    def search_manga(self, query: str, page: int = 1, filters: Optional[Dict[str, Any]] = None) -> List[Manga]:
        manga_list = self.search_manga_request(query, page, filters)
        return [self._convert_to_manga(manga) for manga in manga_list]

    def manga_details_request(self, manga_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/d/{manga_id}"
        response = self.session.get(url, headers=self.headers)
        if response.status_code != 200:
            return {}
        
        soup = self._parse_response(response.text)
        return self._extract_manga_details(soup, manga_id)

    def get_chapter(self, chapter_id: str) -> Chapter:
        url = f"{self.base_url}/d/{chapter_id}"
        response = self.session.get(url, headers=self.headers)
        if response.status_code != 200:
            return Chapter(
                title="Error loading chapter",
                pages=[],
                id=chapter_id
            )
        
        soup = self._parse_response(response.text)
        pages = []
        images = soup.select("img:not([class], [src*=thumb], [src*=cover])")
        
        for index, image in enumerate(images):
            image_url = image.get("src", "")
            if not image_url.startswith("http"):
                image_url = self.base_url + image_url
            
            pages.append(image_url.replace("t.", "."))
        
        return Chapter(
            title="Chapter",
            pages=pages,
            id=chapter_id
        )

    def _convert_to_manga(self, manga_dict: Dict[str, Any]) -> Manga:
        if not manga_dict:
            return None

        manga_id = manga_dict.get("id", "")
        title = manga_dict.get("title", "Unknown")
        author = manga_dict.get("author", manga_dict.get("groups", "Unknown"))
        description = manga_dict.get("description", "")
        poster = manga_dict.get("thumbnail_url", "")
        status = "Completed"
        genres = manga_dict.get("genres", [])
        
        chapter_ids = {"Chapter": manga_id}

        return Manga(
            id=manga_id,
            url=f"/d/{manga_id}",
            title=title,
            author=author,
            description=description,
            poster=poster,
            chapters=1,
            chapter_ids=chapter_ids,
            tags=genres,
            genres=genres,
            status=status
        )

    def _parse_response(self, html_content: str):
        from bs4 import BeautifulSoup
        return BeautifulSoup(html_content, "html.parser")

    def _extract_manga_list(self, soup):
        manga_list = []
        manga_elements = soup.select("a[href*='/d/']")
        
        for element in manga_elements:
            title_element = element.select_one("div")
            title = title_element.text.strip() if title_element else "Unknown"
            
            url = element.get("href", "")
            manga_id = url.split("/")[-1] if url else ""
            
            thumbnail_element = element.select_one("img:not([class])")
            thumbnail_url = thumbnail_element.get("src", "") if thumbnail_element else ""
            if thumbnail_url and not thumbnail_url.startswith("http"):
                thumbnail_url = self.base_url + thumbnail_url
            
            manga = {
                "id": manga_id,
                "title": title,
                "url": url,
                "thumbnail_url": thumbnail_url
            }
            
            manga_list.append(manga)
        
        return manga_list

    def _extract_manga_details(self, soup, manga_id: str) -> Dict[str, Any]:
        title_element = soup.select_one("h1 > span")
        title = title_element.text.strip() if title_element else f"Gallery #{manga_id}"
        
        authors = soup.select("a[href*=/groups/]")
        authors_text = ", ".join([author.text.strip() for author in authors])
        
        artists = soup.select("a[href*=/artists/]")
        artists_text = ", ".join([artist.text.strip() for artist in artists])
        
        author = authors_text if authors_text else artists_text
        artist = artists_text if artists_text else authors_text
        
        tag_elements = soup.select("a[href*=/tags/]")
        genres = []
        for tag in tag_elements:
            tag_text = tag.text.strip()
            tag_text = self._capitalize_each(tag_text)
            if "male" in tag_text.lower():
                tag_text = tag_text.replace("(female)", "♀").replace("(male)", "♂")
            else:
                tag_text = f"{tag_text} ◊"
            genres.append(tag_text)
        
        thumbnail_element = soup.select_one("img[src*=thumbnail].w-96")
        thumbnail_url = thumbnail_element.get("src", "") if thumbnail_element else ""
        if thumbnail_url and not thumbnail_url.startswith("http"):
            thumbnail_url = self.base_url + thumbnail_url
        
        description_parts = []
        
        characters = soup.select("a[href*=/characters/]")
        characters_text = ", ".join([self._capitalize_each(char.text.strip()) for char in characters])
        if characters_text:
            description_parts.append(f"Characters: {characters_text}")
        
        series = soup.select("a[href*=/series/]")
        series_text = ", ".join([self._capitalize_each(s.text.strip()) for s in series])
        if series_text:
            description_parts.append(f"Series: {series_text}")
        
        groups = soup.select("a[href*=/groups/]")
        groups_text = ", ".join([self._capitalize_each(g.text.strip()) for g in groups])
        if groups_text:
            description_parts.append(f"Groups: {groups_text}")
        
        languages = soup.select("a[href*=/language/]")
        languages_text = ", ".join([self._capitalize_each(lang.text.strip()) for lang in languages])
        if languages_text:
            description_parts.append(f"Languages: {languages_text}")
        
        pages_elements = soup.select("div.tag-container")
        for element in pages_elements:
            if "pages:" in element.text:
                description_parts.append(element.text.strip())
                break
        
        description = "\n\n".join(description_parts)
        
        manga_details = {
            "id": manga_id,
            "title": title,
            "author": author,
            "artist": artist,
            "description": description,
            "thumbnail_url": thumbnail_url,
            "genres": genres,
            "status": "Completed"
        }
        
        return manga_details

    def _capitalize_each(self, text: str) -> str:
        return " ".join(word.capitalize() for word in text.split())

    def _get_filters(self) -> Dict[str, Any]:
        return {
            "sort_options": [
                {"name": "Recent", "value": ""},
                {"name": "Popular: All Time", "value": "popular"},
                {"name": "Popular: Week", "value": "popular-7d"},
                {"name": "Popular: Today", "value": "popular-24h"}
            ],
            "tag_types": [
                "tags",
                "male_tags",
                "female_tags",
                "series",
                "characters",
                "artist",
                "groups",
                "language",
                "page"
            ]
        }
