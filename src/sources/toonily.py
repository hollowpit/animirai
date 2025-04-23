
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
            scraper_version="1.0.1"
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
        # In Toonily.kt, it's using ajax for load more
        if page > 1:
            # Using the madara_load_more action from Madara.kt
            form_data = {
                "action": "madara_load_more",
                "page": str(page - 1),
                "template": "madara-core/content/content-archive",
                "vars[orderby]": "meta_value_num",
                "vars[paged]": "1",
                "vars[post_type]": "wp-manga",
                "vars[post_status]": "publish",
                "vars[meta_key]": "_wp_manga_views",
                "vars[order]": "desc",
                "vars[sidebar]": "right",
                "vars[manga_archives_item_layout]": "big_thumbnail"
            }
            
            xhr_headers = self.headers.copy()
            xhr_headers["X-Requested-With"] = "XMLHttpRequest"
            
            try:
                response = self.session.post(
                    f"{self.base_url}/wp-admin/admin-ajax.php",
                    headers=xhr_headers,
                    cookies=self.cookies,
                    data=form_data,
                    timeout=30
                )
                if response.status_code != 200:
                    print(f"Error: Status code {response.status_code} for ajax request")
                    return []
                
                soup = BeautifulSoup(response.text, "html.parser")
                result = self._parse_manga_list(soup)
                print(f"Popular manga request (ajax) found {len(result)} items")
                return result
            except Exception as e:
                print(f"Error in popular_manga_request ajax: {e}")
                return []
        else:
            # First page uses normal GET request
            url = f"{self.base_url}/series/?m_orderby=views"
            try:
                response = self.session.get(
                    url, 
                    headers=self.headers,
                    cookies=self.cookies,
                    timeout=30
                )
                if response.status_code != 200:
                    print(f"Error: Status code {response.status_code} for URL {url}")
                    return []
                
                soup = BeautifulSoup(response.text, "html.parser")
                result = self._parse_manga_list(soup)
                print(f"Popular manga request found {len(result)} items")
                return result
            except Exception as e:
                print(f"Error in popular_manga_request: {e}")
                return []

    def popular_manga(self, page: int = 1) -> List[Manga]:
        manga_list = self.popular_manga_request(page)
        return [self._convert_to_manga(manga) for manga in manga_list]

    def latest_manga_request(self, page: int = 1) -> List[Dict[str, Any]]:
        # In Toonily.kt, it's using ajax for load more
        if page > 1:
            # Using the madara_load_more action from Madara.kt
            form_data = {
                "action": "madara_load_more",
                "page": str(page - 1),
                "template": "madara-core/content/content-archive",
                "vars[orderby]": "meta_value_num",
                "vars[paged]": "1",
                "vars[post_type]": "wp-manga",
                "vars[post_status]": "publish",
                "vars[meta_key]": "_latest_update",
                "vars[order]": "desc",
                "vars[sidebar]": "right",
                "vars[manga_archives_item_layout]": "big_thumbnail"
            }
            
            xhr_headers = self.headers.copy()
            xhr_headers["X-Requested-With"] = "XMLHttpRequest"
            
            try:
                response = self.session.post(
                    f"{self.base_url}/wp-admin/admin-ajax.php",
                    headers=xhr_headers,
                    cookies=self.cookies,
                    data=form_data,
                    timeout=30
                )
                if response.status_code != 200:
                    print(f"Error: Status code {response.status_code} for ajax request")
                    return []
                
                soup = BeautifulSoup(response.text, "html.parser")
                result = self._parse_manga_list(soup)
                print(f"Latest manga request (ajax) found {len(result)} items")
                return result
            except Exception as e:
                print(f"Error in latest_manga_request ajax: {e}")
                return []
        else:
            # First page uses normal GET request
            url = f"{self.base_url}/series/?m_orderby=latest"
            try:
                response = self.session.get(
                    url, 
                    headers=self.headers,
                    cookies=self.cookies,
                    timeout=30
                )
                if response.status_code != 200:
                    print(f"Error: Status code {response.status_code} for URL {url}")
                    return []
                
                soup = BeautifulSoup(response.text, "html.parser")
                result = self._parse_manga_list(soup)
                print(f"Latest manga request found {len(result)} items")
                return result
            except Exception as e:
                print(f"Error in latest_manga_request: {e}")
                return []

    def latest_manga(self, page: int = 1) -> List[Manga]:
        manga_list = self.latest_manga_request(page)
        return [self._convert_to_manga(manga) for manga in manga_list]

    def search_manga_request(self, query: str, page: int = 1, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        filters = filters or {}
        
        if query.startswith("id:"):
            manga_id = query[3:]
            manga_details = self.manga_details_request(manga_id)
            return [manga_details] if manga_details else []
        
        # Replace special characters just like in Toonily.kt
        query = re.sub(r'[^a-z0-9]+', ' ', query.lower()).strip()
        
        url = f"{self.base_url}/search/{page if page > 1 else ''}"
        params = {
            "s": query,
            "post_type": "wp-manga"
        }
        
        if filters:
            if "genres" in filters:
                genres = filters["genres"].split(",")
                for genre in genres:
                    params[f"genre[]"] = genre.strip()
            
            if "status" in filters:
                params["status"] = filters['status']
                
            if "orderby" in filters:
                params["m_orderby"] = filters['orderby']
        
        try:
            full_url = url + "?" + "&".join([f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items()])
            print(f"Search URL: {full_url}")
            response = self.session.get(
                full_url, 
                headers=self.headers,
                cookies=self.cookies,
                timeout=30
            )
            if response.status_code != 200:
                print(f"Error: Status code {response.status_code} for URL {full_url}")
                return []
            
            soup = BeautifulSoup(response.text, "html.parser")
            result = self._parse_search_results(soup)
            print(f"Search manga request found {len(result)} items")
            return result
        except Exception as e:
            print(f"Error in search_manga_request: {e}")
            return []

    def search_manga(self, query: str, page: int = 1, filters: Optional[Dict[str, Any]] = None) -> List[Manga]:
        manga_list = self.search_manga_request(query, page, filters)
        return [self._convert_to_manga(manga) for manga in manga_list]

    def _parse_search_results(self, soup) -> List[Dict[str, Any]]:
        manga_list = []
        
        # Use the selector from Toonily.kt for search
        manga_elements = soup.select("div.c-tabs-item__content, .manga__item")
        
        print(f"Found {len(manga_elements)} search manga elements")
        
        for element in manga_elements:
            try:
                # Find the link
                link_element = element.select_one("div.post-title a") or element.select_one("a")
                if not link_element:
                    continue
                
                url = link_element.get("href", "")
                if not url:
                    continue
                
                # Get ID from URL
                manga_id = url.split("/")[-2] if url.endswith("/") else url.split("/")[-1]
                
                # Get title
                title = link_element.text.strip()
                
                # Get thumbnail
                thumbnail_element = element.select_one("img")
                thumbnail_url = ""
                if thumbnail_element:
                    thumbnail_url = thumbnail_element.get("data-src") or thumbnail_element.get("data-lazy-src") or thumbnail_element.get("src") or ""
                
                # Remove thumbnail size suffix to get higher quality
                if thumbnail_url:
                    thumbnail_url = re.sub(r'-\d+x\d+(\.\w+)$', r'\1', thumbnail_url)
                
                # Get genres
                genre_elements = element.select(".mg_genres .mg_genre") or element.select(".genres-content a")
                genres = [g.text.strip() for g in genre_elements]
                
                # Get status
                status_element = element.select_one(".mg_status") or element.select_one(".status")
                status = status_element.text.strip() if status_element else "Ongoing"
                
                # Get chapters
                chapters = []
                latest_chapters = element.select(".chapter-item .chapter a") or element.select(".chapter a")
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
                    "description": "",
                    "genres": genres,
                    "status": status,
                    "chapters": chapters
                })
            except Exception as e:
                print(f"Error parsing search manga: {e}")
                continue
        
        return manga_list

    def manga_details_request(self, manga_id: str) -> Dict[str, Any]:
        if manga_id.isdigit():
            url = f"{self.base_url}/manga?p={manga_id}"
        else:
            # Try both serie and webtoon paths as Toonily uses both
            url = f"{self.base_url}/serie/{manga_id}"
        
        print(f"Loading manga details from URL: {url}")
        
        try:
            response = self.session.get(
                url, 
                headers=self.headers,
                cookies=self.cookies,
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"Error: Status code {response.status_code} for URL {url}")
                # Try the webtoon path as fallback
                fallback_url = f"{self.base_url}/webtoon/{manga_id}"
                print(f"Trying fallback URL: {fallback_url}")
                
                response = self.session.get(
                    fallback_url,
                    headers=self.headers,
                    cookies=self.cookies,
                    timeout=30
                )
                
                if response.status_code != 200:
                    print(f"Error: Status code {response.status_code} for fallback URL")
                    return {}
            
            soup = BeautifulSoup(response.text, "html.parser")
            return self._parse_manga_details(soup, manga_id)
        except Exception as e:
            print(f"Error in manga_details_request: {e}")
            return {}

    def get_chapter(self, chapter_id: str) -> Chapter:
        # Add the style=list query parameter as done in Toonily.kt
        url = f"{self.base_url}/webtoon/{chapter_id}?style=list"
        print(f"Loading chapter from URL: {url}")
        
        try:
            response = self.session.get(
                url, 
                headers=self.headers,
                cookies=self.cookies,
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"Error: Status code {response.status_code} for chapter URL {url}")
                return Chapter(
                    title="Error loading chapter",
                    pages=[],
                    id=chapter_id
                )
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Get chapter title
            title_element = soup.select_one(".c-breadcrumb .breadcrumb li:last-child") or soup.select_one(".entry-title")
            title = title_element.text.strip() if title_element else "Chapter"
            
            # Get pages using the same selector from Madara.kt
            pages = []
            # Try various selectors used in Madara-based sites
            containers = soup.select(".reading-content img")
            if not containers:
                containers = soup.select("div.page-break img, li.blocks-gallery-item img, .reading-content .text-left img")
            if not containers:
                containers = soup.select(".entry-content img")
            
            print(f"Found {len(containers)} image containers")
            
            for img_element in containers:
                # Use same image extraction logic as in Madara.kt
                img_url = None
                if img_element.has_attr("data-src"):
                    img_url = img_element.get("data-src")
                elif img_element.has_attr("data-lazy-src"):
                    img_url = img_element.get("data-lazy-src")
                elif img_element.has_attr("srcset"):
                    srcset = img_element.get("srcset")
                    # Get the highest quality image from srcset
                    if srcset:
                        srcset_urls = [u.strip().split(" ")[0] for u in srcset.split(",") if u.strip()]
                        if srcset_urls:
                            img_url = srcset_urls[-1]  # Last one is usually highest quality
                elif img_element.has_attr("src"):
                    img_url = img_element.get("src")
                
                if img_url:
                    # Fix relative URLs
                    if img_url.startswith("/"):
                        img_url = f"{self.base_url}{img_url}"
                    elif not img_url.startswith(("http:", "https:")):
                        img_url = f"{self.base_url}/{img_url}"
                    pages.append(img_url)
            
            print(f"Extracted {len(pages)} page URLs")
            
            return Chapter(
                title=title,
                pages=pages,
                id=chapter_id
            )
        except Exception as e:
            print(f"Error loading chapter: {e}")
            return Chapter(
                title="Error loading chapter",
                pages=[],
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
            
        # If we have chapters from the list view, they're incomplete
        # We'll load all chapters when viewing manga details
        chapters_count = len(chapter_ids)
        if chapters_count <= 3 and manga_dict.get("url"):
            # This is probably from list view with limited chapters
            # Set to 999 to indicate we need to load full details
            chapters_count = 999

        return Manga(
            id=manga_id,
            url=manga_dict.get("url", ""),
            title=title,
            author=author,
            description=description,
            poster=poster,
            chapters=chapters_count,
            chapter_ids=chapter_ids,
            tags=genres,
            genres=genres,
            status=status
        )

    def _parse_manga_list(self, soup) -> List[Dict[str, Any]]:
        manga_list = []
        
        # Use the same selector as Toonily.kt (from the Madara parent class)
        # "div.page-item-detail:not(:has(a[href*='bilibilicomics.com'])).manga"
        manga_elements = soup.select("div.page-item-detail.manga, .manga__item")
            
        print(f"Found {len(manga_elements)} manga elements")
        
        for element in manga_elements:
            try:
                # Find the link - try different possible selectors
                link_element = element.select_one(".tab-thumb a") or element.select_one("a.thumb") or element.select_one(".entry-title a") or element.select_one("a")
                if not link_element:
                    continue
                
                url = link_element.get("href", "")
                if not url:
                    continue
                
                # Get ID from URL
                manga_id = url.split("/")[-2] if url.endswith("/") else url.split("/")[-1]
                
                # Get title - try different possible selectors
                title_element = element.select_one(".post-title h3 a") or element.select_one(".entry-title a") or element.select_one("h3 a") or link_element
                title = title_element.text.strip() if title_element else "Unknown"
                
                # Get thumbnail
                thumbnail_element = link_element.select_one("img") or element.select_one("img")
                thumbnail_url = ""
                if thumbnail_element:
                    thumbnail_url = thumbnail_element.get("data-src") or thumbnail_element.get("data-lazy-src") or thumbnail_element.get("src") or ""
                
                # Remove thumbnail size suffix to get higher quality
                if thumbnail_url:
                    thumbnail_url = re.sub(r'-\d+x\d+(\.\w+)$', r'\1', thumbnail_url)
                
                # Get description (not available in list view)
                description = ""
                
                # Get genres
                genre_elements = element.select(".mg_genres .mg_genre") or element.select(".genres-content a")
                genres = [g.text.strip() for g in genre_elements]
                
                # Get rating
                rating_element = element.select_one(".score") or element.select_one(".rating-score")
                rating = 0.0
                if rating_element:
                    try:
                        rating = float(rating_element.text.strip())
                    except ValueError:
                        rating = 0.0
                
                # Get status
                status_element = element.select_one(".mg_status") or element.select_one(".status")
                status = status_element.text.strip() if status_element else "Ongoing"
                
                # Get chapters - in list view we'll only get the latest few
                chapters = []
                latest_chapters = element.select(".chapter-item .chapter a") or element.select(".chapter a") or element.select(".list-chapter .chapter-item a")
                for chapter in latest_chapters:
                    chapter_url = chapter.get("href", "")
                    chapter_id = chapter_url.split("/")[-2] if chapter_url.endswith("/") else chapter_url.split("/")[-1]
                    chapter_title = chapter.text.strip()
                    chapters.append({
                        "id": chapter_id,
                        "title": chapter_title,
                        "url": chapter_url
                    })
                
                # In list view, we only get a few chapters per manga
                # When converted to Manga object, set chapters to 999 to indicate
                # full chapter list will be retrieved on manga details
                
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
            except Exception as e:
                print(f"Error parsing manga: {e}")
                continue
        
        return manga_list

    def _parse_manga_details(self, soup, manga_id: str) -> Dict[str, Any]:
        try:
            # Get title
            title_element = soup.select_one(".post-title h1") or soup.select_one(".entry-title")
            title = title_element.text.strip() if title_element else "Unknown"
            
            # Get URL
            url_element = soup.select_one('link[rel="canonical"]')
            url = url_element.get("href", "") if url_element else f"{self.base_url}/serie/{manga_id}"
            
            # Get thumbnail
            thumbnail_element = soup.select_one(".summary_image img") or soup.select_one(".tab-summary img")
            thumbnail_url = ""
            if thumbnail_element:
                thumbnail_url = thumbnail_element.get("data-src") or thumbnail_element.get("data-lazy-src") or thumbnail_element.get("src") or ""
            
            # Remove thumbnail size suffix to get higher quality
            if thumbnail_url:
                thumbnail_url = re.sub(r'-\d+x\d+(\.\w+)$', r'\1', thumbnail_url)
            
            # Get description
            description_element = soup.select_one(".summary__content .description-summary") or soup.select_one(".summary__content") or soup.select_one(".description-summary")
            description = description_element.text.strip() if description_element else ""
            
            # Get genres
            genre_elements = soup.select(".genres-content a")
            genres = [g.text.strip() for g in genre_elements]
            
            # Get author
            author_elements = soup.select(".author-content a")
            author = ", ".join([a.text.strip() for a in author_elements]) if author_elements else "Unknown"
            
            # Get status
            status_element = soup.select_one(".post-status .summary-content") or soup.select_one(".post-status")
            status = status_element.text.strip() if status_element else "Ongoing"
            
            # Get chapters
            chapters = []
            chapter_elements = soup.select(".wp-manga-chapter") or soup.select(".main.version-chap li") or soup.select(".listing-chapters_wrap li")
            
            print(f"Found {len(chapter_elements)} chapter elements")
            
            for chapter in chapter_elements:
                link = chapter.select_one("a")
                if not link:
                    continue
                
                chapter_url = link.get("href", "")
                
                # Extract the chapter ID from URL
                # Different ways to parse the URL (for Toonily.com)
                if "/webtoon/" in chapter_url:
                    # Extract ID after /webtoon/ in URL
                    match = re.search(r'/webtoon/[^/]+/([^/]+)', chapter_url)
                    if match:
                        chapter_id = match.group(1)
                    else:
                        # Fallback to just using the last part of the URL
                        chapter_id = chapter_url.split("/")[-2] if chapter_url.endswith("/") else chapter_url.split("/")[-1]
                else:
                    # Standard Madara pattern
                    chapter_id = chapter_url.split("/")[-2] if chapter_url.endswith("/") else chapter_url.split("/")[-1]
                
                chapter_title = link.text.strip()
                
                # Get release date if available
                date_element = chapter.select_one(".chapter-release-date") or chapter.select_one(".chapter-time") or chapter.select_one(".post-on")
                release_date = date_element.text.strip() if date_element else ""
                
                chapters.append({
                    "id": chapter_id,
                    "title": chapter_title,
                    "url": chapter_url,
                    "release_date": release_date
                })
            
            result = {
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
            print(f"Parsed manga details: {title} with {len(chapters)} chapters")
            return result
        except Exception as e:
            print(f"Error parsing manga details: {e}")
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
