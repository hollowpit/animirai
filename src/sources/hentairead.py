
import json
import re
import time
import urllib.parse
import base64
import requests
import cloudscraper
from typing import List, Dict, Any, Optional, Tuple
from bs4 import BeautifulSoup
from datetime import datetime
from src.lib.types import Scraper, Manga, Chapter

class HentaiRead(Scraper):
    def __init__(self):
        super().__init__(
            name="HentaiRead",
            url="https://hentairead.com",
            api_url="https://hentairead.com/wp-admin/admin-ajax.php",
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
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": self.base_url,
            "Connection": "keep-alive"
        }
        self.cdn_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Referer": self.base_url,
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": self.base_url,
            "Connection": "keep-alive"
        }

    def popular_manga_request(self, page: int = 1) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/hentai/page/{page}/?sortby=views"
        
        response = self.session.get(url, headers=self.headers)
        if response.status_code != 200:
            return []
        
        soup = BeautifulSoup(response.text, "html.parser")
        return self._extract_manga_list(soup)

    def popular_manga(self, page: int = 1) -> List[Manga]:
        manga_list = self.popular_manga_request(page)
        return [self._convert_to_manga(manga) for manga in manga_list]

    def latest_manga_request(self, page: int = 1) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/hentai/page/{page}/?sortby=new"
        
        response = self.session.get(url, headers=self.headers)
        if response.status_code != 200:
            return []
        
        soup = BeautifulSoup(response.text, "html.parser")
        return self._extract_manga_list(soup)

    def latest_manga(self, page: int = 1) -> List[Manga]:
        manga_list = self.latest_manga_request(page)
        return [self._convert_to_manga(manga) for manga in manga_list]

    def search_manga_request(self, query: str, page: int = 1, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        filters = filters or {}
        
        if not query and not filters:
            return self.latest_manga_request(page)
        
        if filters:
            url = f"{self.base_url}/page/{page}"
            params = {"s": query, "title-type": "contains"}
            
            for filter_key, filter_value in filters.items():
                if filter_key == "types" and filter_value:
                    for type_val in filter_value:
                        params.setdefault("categories[]", []).append(type_val)
                elif filter_key == "sort" and filter_value:
                    params["sortby"] = filter_value
                    params["order"] = filters.get("order", "desc")
                elif filter_key == "pages" and filter_value:
                    min_pages, max_pages = self._parse_page_range(filter_value)
                    params["pages"] = f"{min_pages}-{max_pages}"
                elif filter_key == "uploaded" and filter_value:
                    release_type = "in"
                    release_year = filter_value
                    
                    if filter_value.startswith(">"):
                        release_type = "after"
                        release_year = filter_value[1:].strip()
                    elif filter_value.startswith("<"):
                        release_type = "before"
                        release_year = filter_value[1:].strip()
                    
                    params["release-type"] = release_type
                    params["release"] = release_year.strip()
                elif filter_key in ["tags", "artists", "circles", "characters", "collections", "scanlators", "conventions"]:
                    if filter_value:
                        tag_type_map = {
                            "tags": "manga_tag",
                            "artists": "artist",
                            "circles": "circle",
                            "characters": "character",
                            "collections": "collection",
                            "scanlators": "scanlator",
                            "conventions": "convention"
                        }
                        
                        tag_type = tag_type_map.get(filter_key, "manga_tag")
                        tags = filter_value.split(",")
                        
                        for tag in tags:
                            tag = tag.strip()
                            if not tag:
                                continue
                                
                            exclude = tag.startswith("-") and tag_type == "manga_tag"
                            tag_value = tag[1:].strip() if exclude else tag
                            tag_id = self._get_tag_id(tag_value, tag_type)
                            
                            if tag_id:
                                if exclude:
                                    params.setdefault("excluding[]", []).append(str(tag_id))
                                elif tag_type == "manga_tag":
                                    params.setdefault("including[]", []).append(str(tag_id))
                                else:
                                    params.setdefault(f"{tag_type}s[]", []).append(str(tag_id))
            
            params_str = "&".join([
                f"{k}={v}" if not isinstance(v, list) else "&".join([f"{k}={item}" for item in v])
                for k, v in params.items()
            ])
            
            request_url = f"{url}?{params_str}"
            
        else:
            request_url = f"{self.base_url}/page/{page}?s={urllib.parse.quote(query)}"
        
        response = self.session.get(request_url, headers=self.headers)
        if response.status_code != 200:
            return []
        
        soup = BeautifulSoup(response.text, "html.parser")
        return self._extract_manga_list(soup)

    def search_manga(self, query: str, page: int = 1, filters: Optional[Dict[str, Any]] = None) -> List[Manga]:
        manga_list = self.search_manga_request(query, page, filters)
        return [self._convert_to_manga(manga) for manga in manga_list]

    def manga_details_request(self, manga_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/{manga_id}"
        response = self.session.get(url, headers=self.headers)
        if response.status_code != 200:
            return {}
        
        soup = BeautifulSoup(response.text, "html.parser")
        return self._extract_manga_details(soup, manga_id)

    def manga_details(self, manga_id: str) -> Manga:
        manga_dict = self.manga_details_request(manga_id)
        return self._convert_to_manga(manga_dict)

    def get_chapter(self, chapter_id: str) -> Chapter:
        url = f"{self.base_url}/{chapter_id}/english/p/1/"
        response = self.session.get(url, headers=self.headers)
        if response.status_code != 200:
            return Chapter(
                title="Error loading chapter",
                pages=[],
                id=chapter_id
            )
        
        soup = BeautifulSoup(response.text, "html.parser")
        pages = self._extract_chapter_pages(soup)
        
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
        author = manga_dict.get("author", "Unknown")
        description = manga_dict.get("description", "")
        poster = manga_dict.get("thumbnail_url", "")
        
        status = "Completed"
        
        genres = manga_dict.get("genres", [])
        tags = manga_dict.get("tags", [])
        
        chapter_ids = {"Chapter": manga_id}

        return Manga(
            id=manga_id,
            url=manga_id,
            title=title,
            author=author,
            description=description,
            poster=poster,
            chapters=1,
            chapter_ids=chapter_ids,
            tags=tags,
            genres=genres,
            status=status
        )

    def _extract_manga_list(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        manga_list = []
        manga_elements = soup.select(".manga-item")
        
        for element in manga_elements:
            url_element = element.select_one(".manga-item__link")
            if not url_element:
                continue
                
            url = url_element.get("href", "")
            manga_id = url.split("/")[-2] if url.endswith("/") else url.split("/")[-1]
            
            title_element = element.select_one("h3")
            title = title_element.text.strip() if title_element else "Unknown"
            
            thumbnail_element = element.select_one("img")
            thumbnail_url = None
            if thumbnail_element:
                thumbnail_url = thumbnail_element.get("data-src") or thumbnail_element.get("data-lazy-src") or thumbnail_element.get("src")
            
            manga = {
                "id": manga_id,
                "title": title,
                "url": url,
                "thumbnail_url": thumbnail_url
            }
            
            manga_list.append(manga)
        
        return manga_list

    def _extract_manga_details(self, soup: BeautifulSoup, manga_id: str) -> Dict[str, Any]:
        title_element = soup.select_one("h1")
        title = title_element.text.strip() if title_element else f"Gallery #{manga_id}"
        
        authors_elements = soup.select("a[href*=/circle/] span:first-of-type")
        authors = [author.text.strip() for author in authors_elements]
        
        artists_elements = soup.select("a[href*=/artist/] span:first-of-type")
        artists = [artist.text.strip() for artist in artists_elements]
        
        author = ", ".join(authors) or ", ".join(artists)
        artist = ", ".join(artists) or ", ".join(authors)
        
        tags_elements = soup.select("a[href*=/tag/] span:first-of-type")
        tags = [tag.text.strip() for tag in tags_elements]
        
        thumbnail_element = soup.select_one(".c-manga-cover img")
        thumbnail_url = None
        if thumbnail_element:
            thumbnail_url = thumbnail_element.get("data-src") or thumbnail_element.get("data-lazy-src") or thumbnail_element.get("src")
        
        description_parts = []
        
        characters_elements = soup.select("a[href*=/characters/] span:first-of-type")
        characters = [self._capitalize_each(char.text.strip()) for char in characters_elements]
        if characters:
            description_parts.append(f"Characters: {', '.join(characters)}")
        
        parodies_elements = soup.select("a[href*=/parody/] span:first-of-type")
        parodies = [self._capitalize_each(parody.text.strip()) for parody in parodies_elements]
        if parodies:
            description_parts.append(f"Parodies: {', '.join(parodies)}")
        
        circles_elements = soup.select("a[href*=/circle/] span:first-of-type")
        circles = [self._capitalize_each(circle.text.strip()) for circle in circles_elements]
        if circles:
            description_parts.append(f"Circles: {', '.join(circles)}")
        
        conventions_elements = soup.select("a[href*=/convention/] span:first-of-type")
        conventions = [self._capitalize_each(convention.text.strip()) for convention in conventions_elements]
        if conventions:
            description_parts.append(f"Convention: {', '.join(conventions)}")
        
        scanlators_elements = soup.select("a[href*=/scanlator/] span:first-of-type")
        scanlators = [self._capitalize_each(scanlator.text.strip()) for scanlator in scanlators_elements]
        if scanlators:
            description_parts.append(f"Scanlators: {', '.join(scanlators)}")
        
        alt_titles_element = soup.select_one(".manga-titles h2")
        if alt_titles_element and alt_titles_element.text.strip():
            alt_titles = alt_titles_element.text.split("|")
            formatted_titles = "\n".join([f"- {title.strip()}" for title in alt_titles])
            description_parts.append(f"Alternative Titles: \n{formatted_titles}")
        
        # Find element with pages count using a more compatible approach
        pages_elements = soup.select(".items-center")
        for element in pages_elements:
            if "pages:" in element.text.lower():
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
            "tags": tags,
            "genres": tags
        }
        
        return manga_details

    def _extract_chapter_pages(self, soup: BeautifulSoup) -> List[str]:
        pages = []
        
        chapter_extra_data = soup.select_one("#single-chapter-js-extra")
        base_url = None
        
        if chapter_extra_data:
            data_content = chapter_extra_data.string
            match = re.search(r'= (\{[^;]+)', data_content)
            if match:
                try:
                    json_data = json.loads(match.group(1))
                    base_url = json_data.get("baseUrl")
                except:
                    pass
        
        chapter_data = soup.select_one("#single-chapter-js-before")
        if chapter_data:
            data_content = chapter_data.string
            match = re.search(r'.(ey\S+).\s', data_content)
            if match and base_url:
                try:
                    encoded_data = match.group(1)
                    decoded_data = base64.b64decode(encoded_data).decode('utf-8')
                    json_data = json.loads(decoded_data)
                    
                    images = json_data.get("data", {}).get("chapter", {}).get("images", [])
                    for image in images:
                        if image.get("src"):
                            pages.append(f"{base_url}/{image.get('src')}")
                except:
                    pass
        
        return pages

    def _get_tag_id(self, tag: str, tag_type: str) -> Optional[int]:
        url = f"{self.api_url}?action=search_manga_terms&search={urllib.parse.quote(tag)}&taxonomy={tag_type}"
        if tag_type == "artist":
            url = url.replace("artist", "manga_artist")
            
        response = self.session.get(url, headers=self.headers)
        if response.status_code != 200:
            return None
            
        try:
            data = response.json()
            results = data.get("results", [])
            matching_items = [item for item in results if item.get("text", "").lower() == tag.lower()]
            
            if matching_items:
                return matching_items[0].get("id")
                
        except:
            pass
            
        return None

    def _parse_page_range(self, query: str, min_pages: int = 1, max_pages: int = 9999) -> Tuple[int, int]:
        digits = "".join(c for c in query if c.isdigit())
        num = int(digits) if digits else -1
        
        if num < 0:
            return min_pages, max_pages
            
        if query.startswith("<"):
            if len(query) > 1 and query[1] == "=":
                return min_pages, min(num, max_pages)
            return min_pages, min(num - 1, max_pages)
        elif query.startswith(">"):
            if len(query) > 1 and query[1] == "=":
                return max(min_pages, num), max_pages
            return max(min_pages, num + 1), max_pages
        elif query.startswith("="):
            if len(query) > 1:
                if query[1] == ">":
                    return max(min_pages, num), max_pages
                elif query[1] == "<":
                    return min_pages, min(num, max_pages)
            return max(min_pages, num), min(num, max_pages)
        else:
            return max(min_pages, num), min(num, max_pages)

    def _capitalize_each(self, text: str) -> str:
        return " ".join(word.capitalize() for word in text.split())

    def _get_filters(self) -> Dict[str, Any]:
        return {
            "sort_options": [
                {"name": "Latest", "value": "new"},
                {"name": "A-Z", "value": "alphabet"},
                {"name": "Rating", "value": "rating"},
                {"name": "Views", "value": "views"}
            ],
            "types": [
                {"name": "Doujinshi", "value": "4"},
                {"name": "Manga", "value": "52"},
                {"name": "Artist CG", "value": "4798"}
            ]
        }
