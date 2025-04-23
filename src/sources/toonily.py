
import json
import re
import time
import random
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
            api_url=None,
            scraper_version="1.0.0"
        )
        self.available_filters = self._get_filters()
        self.lang = "en"
        self.session = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False
            },
            delay=8,  # Add delay between requests
            interpreter='nodejs'  # Use nodejs interpreter for better CF bypass
        )
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
            "Referer": f"{self.base_url}/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "max-age=0",
            "Sec-Ch-Ua": '"Not A(Brand";v="99", "Microsoft Edge";v="120", "Chromium";v="120"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "Origin": self.base_url,
            "Connection": "keep-alive",
        }
        self.cookie = {"toonily-mature": "1"}
        self.manga_sub_string = "serie"
        self.filter_non_manga_items = False
        self.date_format = "%b %d, %y"
        self.title_special_characters_regex = re.compile(r"[^a-z0-9]+")
        self.sd_cover_regex = re.compile(r"-[0-9]+x[0-9]+(\.\w+)$")
        self.genres_list = []
        self.genres_fetched = False

    def popular_manga_request(self, page: int = 1) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/{self.manga_sub_string}/page/{page}/?m_orderby=views"
        
        response = self.session.get(url, headers=self.headers, cookies=self.cookie)
        if response.status_code != 200:
            return []
        
        soup = BeautifulSoup(response.text, "html.parser")
        return self._extract_manga_list(soup)

    def popular_manga(self, page: int = 1) -> List[Manga]:
        manga_list = self.popular_manga_request(page)
        return [self._convert_to_manga(manga) for manga in manga_list]

    def latest_manga_request(self, page: int = 1) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/{self.manga_sub_string}/page/{page}/?m_orderby=latest"
        
        response = self.session.get(url, headers=self.headers, cookies=self.cookie)
        if response.status_code != 200:
            return []
        
        soup = BeautifulSoup(response.text, "html.parser")
        return self._extract_manga_list(soup)

    def latest_manga(self, page: int = 1) -> List[Manga]:
        manga_list = self.latest_manga_request(page)
        return [self._convert_to_manga(manga) for manga in manga_list]

    def search_manga_request(self, query: str, page: int = 1, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        # Clean query
        query = self.title_special_characters_regex.sub(" ", query).strip()
        
        if query.startswith("id:"):
            slug = query[3:]
            url = f"{self.base_url}/{self.manga_sub_string}/{slug}/"
            response = self.session.get(url, headers=self.headers, cookies=self.cookie)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                manga_details = self._extract_manga_details(soup, slug)
                return [manga_details] if manga_details else []
            return []
        
        url = f"{self.base_url}/?s={query}&post_type=wp-manga"
        
        if filters:
            for key, value in filters.items():
                if key == "genre" and value:
                    for genre in value.split(","):
                        if genre.strip():
                            url += f"&genre[]={genre.strip()}"
                elif key == "author" and value:
                    url += f"&author={value}"
                elif key == "artist" and value:
                    url += f"&artist={value}"
                elif key == "year" and value:
                    url += f"&release={value}"
                elif key == "status" and value:
                    for status in value.split(","):
                        if status.strip():
                            url += f"&status[]={status.strip()}"
                elif key == "order" and value:
                    url += f"&m_orderby={value}"
        
        if page > 1:
            url = f"{url}&paged={page}"
        
        response = self.session.get(url, headers=self.headers, cookies=self.cookie)
        if response.status_code != 200:
            return []
        
        soup = BeautifulSoup(response.text, "html.parser")
        return self._extract_search_manga_list(soup)

    def search_manga(self, query: str, page: int = 1, filters: Optional[Dict[str, Any]] = None) -> List[Manga]:
        manga_list = self.search_manga_request(query, page, filters)
        return [self._convert_to_manga(manga) for manga in manga_list]

    def manga_details_request(self, manga_id: str) -> Dict[str, Any]:
        # Ensure URL uses the correct manga subdirectory
        url = f"{self.base_url}/{self.manga_sub_string}/{manga_id}/"
        
        response = self.session.get(url, headers=self.headers, cookies=self.cookie)
        if response.status_code != 200:
            return {}
        
        soup = BeautifulSoup(response.text, "html.parser")
        return self._extract_manga_details(soup, manga_id)

    def get_manga(self, manga_id: str) -> Manga:
        manga_dict = self.manga_details_request(manga_id)
        return self._convert_to_manga(manga_dict)

    def get_chapter(self, chapter_id: str) -> Chapter:
        url = f"{self.base_url}/{chapter_id}"
        
        # Random delay to avoid being detected as a bot
        time.sleep(2 + 3 * random.random())
        
        # First get the cookies from the main page to help bypass Cloudflare
        try:
            self.session.get(self.base_url, headers=self.headers)
        except:
            pass
            
        response = self.session.get(url, headers=self.headers, cookies=self.cookie)
        if response.status_code != 200:
            return Chapter(
                title="Error loading chapter",
                pages=[],
                id=chapter_id
            )
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Get chapter title
        title_element = soup.select_one("ol.breadcrumb li.active")
        title = title_element.text.strip() if title_element else f"Chapter {chapter_id}"
        
        # Get pages
        pages = []
        images = soup.select("div.page-break img, .reading-content .text-left img")
        
        for index, image in enumerate(images):
            image_url = image.get("data-src") or image.get("src") or ""
            if image_url and "images/default-image" not in image_url:
                pages.append(image_url.replace("\t", ''))
        
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
        
        chapters = manga_dict.get("chapters", {})
        
        return Manga(
            id=manga_id,
            url=f"/{self.manga_sub_string}/{manga_id}",
            title=title,
            author=author,
            description=description,
            poster=poster,
            chapters=len(chapters),
            chapter_ids=chapters,
            tags=genres,
            genres=genres,
            status=status
        )

    def _extract_manga_list(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        manga_list = []
        manga_elements = soup.select("div.page-item-detail.manga")
        
        for element in manga_elements:
            title_element = element.select_one("h3.h5 a")
            if not title_element:
                continue
                
            title = title_element.text.strip()
            url = title_element.get("href", "")
            
            manga_id = url.split("/")[-2] if url.endswith("/") else url.split("/")[-1]
            
            thumbnail_element = element.select_one("img")
            thumbnail_url = thumbnail_element.get("data-src") or thumbnail_element.get("src") if thumbnail_element else ""
            
            # Fix HD image URL
            if thumbnail_url and self.sd_cover_regex.search(thumbnail_url):
                thumbnail_url = self.sd_cover_regex.sub(r"\1", thumbnail_url)
            
            # Get chapters for this manga
            chapters = {}
            try:
                chapters = self._fetch_chapter_list(manga_id)
            except Exception:
                pass
            
            manga = {
                "id": manga_id,
                "title": title,
                "url": url,
                "thumbnail_url": thumbnail_url,
                "chapters": chapters
            }
            
            manga_list.append(manga)
        
        return manga_list

    def _extract_search_manga_list(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        manga_list = []
        manga_elements = soup.select("div.c-tabs-item__content")
        
        # If no results with the first selector, try the alternative
        if not manga_elements:
            manga_elements = soup.select("div.page-item-detail.manga")
        
        for element in manga_elements:
            title_element = element.select_one("div.post-title a, h3.h5 a")
            if not title_element:
                continue
                
            title = title_element.text.strip()
            url = title_element.get("href", "")
            
            manga_id = url.split("/")[-2] if url.endswith("/") else url.split("/")[-1]
            
            thumbnail_element = element.select_one("img")
            thumbnail_url = thumbnail_element.get("data-src") or thumbnail_element.get("src") if thumbnail_element else ""
            
            # Fix HD image URL
            if thumbnail_url and self.sd_cover_regex.search(thumbnail_url):
                thumbnail_url = self.sd_cover_regex.sub(r"\1", thumbnail_url)
            
            # Get chapters for this manga
            chapters = {}
            try:
                chapters = self._fetch_chapter_list(manga_id)
            except Exception:
                pass
            
            manga = {
                "id": manga_id,
                "title": title,
                "url": url,
                "thumbnail_url": thumbnail_url,
                "chapters": chapters
            }
            
            manga_list.append(manga)
        
        return manga_list

    def _extract_manga_details(self, soup: BeautifulSoup, manga_id: str) -> Dict[str, Any]:
        # Title
        title_element = soup.select_one("div.post-title h1, div.post-title h3")
        title = title_element.text.strip() if title_element else f"Series {manga_id}"
        
        # Author
        author_elements = soup.select("div.author-content a")
        authors = [author.text.strip() for author in author_elements if not "updating" in author.text.lower()]
        author = ", ".join(authors) if authors else "Unknown"
        
        # Artist
        artist_elements = soup.select("div.artist-content a")
        artists = [artist.text.strip() for artist in artist_elements if not "updating" in artist.text.lower()]
        artist = ", ".join(artists) if artists else author
        
        # Description
        description_element = soup.select_one("div.description-summary div.summary__content, div.summary_content div.post-content_item > h5 + div")
        description = ""
        if description_element:
            paragraphs = description_element.select("p")
            if paragraphs:
                description = "\n\n".join([p.text.strip() for p in paragraphs])
            else:
                description = description_element.text.strip()
        
        # Cover
        thumbnail_element = soup.select_one("div.summary_image img")
        thumbnail_url = ""
        if thumbnail_element:
            thumbnail_url = thumbnail_element.get("data-src") or thumbnail_element.get("src") or ""
            # Fix HD image URL
            if thumbnail_url and self.sd_cover_regex.search(thumbnail_url):
                thumbnail_url = self.sd_cover_regex.sub(r"\1", thumbnail_url)
        
        # Status
        status_element = soup.select_one("div.post-status div.summary-content, div.post-content_item:contains(Status) .summary-content")
        status = "Ongoing"
        if status_element:
            status_text = status_element.text.strip().lower()
            if any(s in status_text for s in ["complete", "completo", "completado", "concluído", "concluido", "finalizado"]):
                status = "Completed"
            elif any(s in status_text for s in ["on hold", "pausado", "en espera"]):
                status = "On Hiatus"
            elif any(s in status_text for s in ["canceled", "cancelado", "cancelled"]):
                status = "Cancelled"
        
        # Genres
        genre_elements = soup.select("div.genres-content a")
        genres = [genre.text.strip() for genre in genre_elements]
        
        # Alternative names
        alt_name_element = soup.select_one(".post-content_item:contains(Alt) .summary-content")
        alt_name = alt_name_element.text.strip() if alt_name_element else ""
        
        if alt_name:
            description = f"{description}\n\nAlternative Names: {alt_name}"
        
        # Get chapters
        chapters = {}
        chapters_wrapper = soup.select("div[id^=manga-chapters-holder]")
        
        if chapters_wrapper:
            manga_url = self.base_url + soup.select_one("meta[property='og:url']").get("content", "").replace(self.base_url, "")
            ajax_url = f"{manga_url}/ajax/chapters"
            
            response = self.session.post(ajax_url, headers={**self.headers, "X-Requested-With": "XMLHttpRequest"}, cookies=self.cookie)
            if response.status_code == 200:
                chapters_soup = BeautifulSoup(response.text, "html.parser")
                chapter_elements = chapters_soup.select("li.wp-manga-chapter")
                
                for element in chapter_elements:
                    chapter_link = element.select_one("a")
                    if chapter_link:
                        chapter_url = chapter_link.get("href", "").replace(self.base_url, "")
                        chapter_name = chapter_link.text.strip()
                        chapter_id = chapter_url
                        chapters[chapter_name] = chapter_id
        
        return {
            "id": manga_id,
            "title": title,
            "author": author,
            "artist": artist,
            "description": description,
            "thumbnail_url": thumbnail_url,
            "genres": genres,
            "status": status,
            "chapters": chapters
        }

    def _fetch_chapter_list(self, manga_id: str) -> Dict[str, str]:
        """Fetch chapters for a manga using its ID"""
        chapters = {}
        
        # Random delay to avoid being detected as a bot
        time.sleep(2 + 3 * random.random())
        
        # Make sure URL uses the correct manga subdirectory
        url = f"{self.base_url}/{self.manga_sub_string}/{manga_id}/"
        
        # First get the cookies from the main page
        try:
            self.session.get(self.base_url, headers=self.headers)
        except:
            pass
            
        # Now get the manga page with cookies from previous request
        response = self.session.get(url, headers=self.headers, cookies=self.cookie)
        if response.status_code != 200:
            return chapters
        
        soup = BeautifulSoup(response.text, "html.parser")
        chapters_wrapper = soup.select("div[id^=manga-chapters-holder]")
        
        if chapters_wrapper:
            ajax_url = f"{url}ajax/chapters"
            
            ajax_response = self.session.post(
                ajax_url, 
                headers={**self.headers, "X-Requested-With": "XMLHttpRequest"}, 
                cookies=self.cookie
            )
            
            if ajax_response.status_code == 200:
                chapters_soup = BeautifulSoup(ajax_response.text, "html.parser")
                chapter_elements = chapters_soup.select("li.wp-manga-chapter")
                
                for element in chapter_elements:
                    chapter_link = element.select_one("a")
                    if chapter_link:
                        chapter_url = chapter_link.get("href", "").replace(self.base_url, "")
                        chapter_name = chapter_link.text.strip()
                        chapters[chapter_name] = chapter_url
        
        # If we didn't get chapters from AJAX, try to get them directly from the page
        if not chapters:
            chapter_elements = soup.select("li.wp-manga-chapter")
            for element in chapter_elements:
                chapter_link = element.select_one("a")
                if chapter_link:
                    chapter_url = chapter_link.get("href", "").replace(self.base_url, "")
                    chapter_name = chapter_link.text.strip()
                    chapters[chapter_name] = chapter_url
            
        return chapters
        

    def _parse_date(self, date_string: str) -> int:
        if not date_string or date_string.lower() == "updating":
            return 0
        
        # Handle "today", "yesterday", etc.
        now = datetime.now()
        
        if "today" in date_string.lower():
            today = datetime(now.year, now.month, now.day)
            return int(today.timestamp() * 1000)
        
        if "yesterday" in date_string.lower():
            yesterday = datetime(now.year, now.month, now.day)
            yesterday = yesterday.replace(day=yesterday.day - 1)
            return int(yesterday.timestamp() * 1000)
        
        if "ago" in date_string.lower():
            # Parse relative date
            number = re.search(r"(\d+)", date_string)
            if not number:
                return 0
            
            num = int(number.group(1))
            
            if "day" in date_string.lower():
                delta = now.replace(day=now.day - num)
            elif "hour" in date_string.lower():
                delta = now.replace(hour=now.hour - num)
            elif "minute" in date_string.lower():
                delta = now.replace(minute=now.minute - num)
            elif "second" in date_string.lower():
                delta = now.replace(second=now.second - num)
            elif "week" in date_string.lower():
                delta = now.replace(day=now.day - (num * 7))
            elif "month" in date_string.lower():
                delta = now.replace(month=now.month - num)
            else:
                return 0
                
            return int(delta.timestamp() * 1000)
            
        # Try to parse with date format
        try:
            dt = datetime.strptime(date_string, self.date_format)
            return int(dt.timestamp() * 1000)
        except Exception:
            return 0

    def _get_filters(self) -> Dict[str, Any]:
        return {
            "status_options": [
                {"name": "Completed", "value": "end"},
                {"name": "Ongoing", "value": "on-going"},
                {"name": "Canceled", "value": "canceled"},
                {"name": "On Hold", "value": "on-hold"},
            ],
            "sort_options": [
                {"name": "Relevance", "value": ""},
                {"name": "Latest", "value": "latest"},
                {"name": "A-Z", "value": "alphabet"},
                {"name": "Rating", "value": "rating"},
                {"name": "Trending", "value": "trending"},
                {"name": "Views", "value": "views"},
                {"name": "New", "value": "new-manga"},
            ],
            "genre_list": [
                {"name": "Action", "value": "action"},
                {"name": "Adult", "value": "adult"},
                {"name": "Adventure", "value": "adventure"},
                {"name": "Comedy", "value": "comedy"},
                {"name": "Drama", "value": "drama"},
                {"name": "Ecchi", "value": "ecchi"},
                {"name": "Fantasy", "value": "fantasy"},
                {"name": "Gender Bender", "value": "gender-bender"},
                {"name": "Harem", "value": "harem"},
                {"name": "Historical", "value": "historical"},
                {"name": "Horror", "value": "horror"},
                {"name": "Josei", "value": "josei"},
                {"name": "Martial Arts", "value": "martial-arts"},
                {"name": "Mature", "value": "mature"},
                {"name": "Mystery", "value": "mystery"},
                {"name": "Psychological", "value": "psychological"},
                {"name": "Romance", "value": "romance"},
                {"name": "School Life", "value": "school-life"},
                {"name": "Sci-fi", "value": "sci-fi"},
                {"name": "Seinen", "value": "seinen"},
                {"name": "Shoujo", "value": "shoujo"},
                {"name": "Shounen", "value": "shounen"},
                {"name": "Slice of Life", "value": "slice-of-life"},
                {"name": "Smut", "value": "smut"},
                {"name": "Sports", "value": "sports"},
                {"name": "Supernatural", "value": "supernatural"},
                {"name": "Tragedy", "value": "tragedy"},
                {"name": "Webtoons", "value": "webtoons"},
            ]
        }


    def download_chapter(self, chapter_id: str, output_dir: str = "test_img") -> bool:
        """Download all images from a chapter to the specified directory
        
        Args:
            chapter_id: The chapter ID to download
            output_dir: Directory to save images to (default: test_img)
            
        Returns:
            bool: True if successful, False otherwise
        """
        import os
        import requests
        from pathlib import Path
        
        # Get chapter info
        chapter = self.get_chapter(chapter_id)
        if not chapter.pages:
            print(f"Error: No pages found for chapter {chapter_id}")
            return False
            
        # Create directory structure
        chapter_dir = Path(output_dir) / chapter_id.replace("/", "_")
        chapter_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"Downloading {len(chapter.pages)} images from {chapter.title} to {chapter_dir}")
        
        # Download each image
        for i, image_url in enumerate(chapter.pages):
            if not image_url:
                continue
                
            # Determine file extension from URL
            ext = image_url.split(".")[-1].lower()
            if ext not in ["jpg", "jpeg", "png", "gif", "webp"]:
                ext = "jpg"  # Default to jpg if extension can't be determined
                
            # Create filename with padding (001.jpg, 002.jpg, etc.)
            filename = f"{i+1:03d}.{ext}"
            filepath = chapter_dir / filename
            
            try:
                # Random delay to avoid being detected as a bot
                time.sleep(1 + 2 * random.random())
                
                # Download the image with referer header
                img_headers = {
                    "User-Agent": self.headers["User-Agent"],
                    "Referer": f"{self.base_url}/{chapter_id}",
                    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8"
                }
                
                response = requests.get(image_url, headers=img_headers, stream=True, timeout=30)
                if response.status_code == 200:
                    with open(filepath, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    print(f"Downloaded {filename} ({i+1}/{len(chapter.pages)})")
                else:
                    print(f"Failed to download {filename}: HTTP {response.status_code}")
            except Exception as e:
                print(f"Error downloading {filename}: {str(e)}")
        
        print(f"Chapter download completed: {chapter.title}")
        return True

