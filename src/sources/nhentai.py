
import json
import re
import time
import requests
import cloudscraper
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from datetime import datetime
from src.lib.types import Scraper, Manga, Chapter

class NHentai(Scraper):
    def __init__(self):
        super().__init__(
            name="NHentai",
            url="https://nhentai.net",
            api_url="https://nhentai.net/api",
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
            "Referer": self.base_url,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
            "sec-ch-ua": '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
            "sec-ch-ua-mobile": "?0"
        }
        self.preferences = {
            "display_full_title": True,
            "media_server": 1
        }
        self.id_search_prefix = "id:"
        self.image_types = {
            "j": "jpg",
            "p": "png",
            "g": "gif",
            "w": "webp"
        }

    def popular_manga_request(self, page: int = 1) -> List[Dict[str, Any]]:
        
        try:
            url = f"{self.base_url}/popular"
            if page > 1:
                url += f"?page={page}"
                
            response = self.session.get(
                url,
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            return self._parse_search_results(soup)
        except Exception as e:
            pass
            return []

    def popular_manga(self, page: int = 1) -> List[Manga]:
        manga_list = self.popular_manga_request(page)
        return [self._convert_to_manga(manga) for manga in manga_list]

    def latest_manga_request(self, page: int = 1) -> List[Dict[str, Any]]:
        
        try:
            url = self.base_url
            if page > 1:
                url += f"?page={page}"
                
            response = self.session.get(
                url,
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            return self._parse_search_results(soup)
        except Exception as e:
            pass
            return []

    def latest_manga(self, page: int = 1) -> List[Manga]:
        manga_list = self.latest_manga_request(page)
        return [self._convert_to_manga(manga) for manga in manga_list]

    def search_manga_request(self, query: str, page: int = 1, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        
        
        filters = filters or {}
        
        if query.startswith(self.id_search_prefix):
            id_value = query[len(self.id_search_prefix):]
            manga_details = self.manga_details_request(id_value)
            return [manga_details] if manga_details else []
        
        if query.isdigit():
            manga_details = self.manga_details_request(query)
            return [manga_details] if manga_details else []
        
        base_search_url = f"{self.base_url}/search"
        url_params = {
            "q": self._build_search_query(query, filters),
            "page": 1
        }
        
        if "sort" in filters:
            url_params["sort"] = filters["sort"]
        
        if filters.get("favorites_only", False):
            base_search_url = f"{self.base_url}/favorites"
        
        try:
            all_results = []
            current_page = 1
            has_next_page = True
            
            while has_next_page:
                url_params["page"] = current_page
                response = self.session.get(
                    base_search_url, 
                    params=url_params, 
                    headers=self.headers,
                    timeout=30
                )
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, "html.parser")
                page_results = self._parse_search_results(soup)
                
                if page_results:
                    all_results.extend(page_results)
                    
                    next_page = soup.select_one("#content > section.pagination > a.next")
                    if next_page:
                        current_page += 1
                    else:
                        has_next_page = False
                else:
                    has_next_page = False
                
                if current_page > 5:
                    break
            
            return all_results
            
        except Exception as e:
            pass
            return []

    def search_manga(self, query: str, page: int = 1, filters: Optional[Dict[str, Any]] = None) -> List[Manga]:
        manga_list = self.search_manga_request(query, page, filters)
        return [self._convert_to_manga(manga) for manga in manga_list]

    def manga_details_request(self, manga_id: str) -> Dict[str, Any]:
        
        
        try:
            response = self.session.get(
                f"{self.base_url}/g/{manga_id}/",
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            script_data = soup.select_one("#__nuxt")
            if not script_data:
                script_data = soup.select_one("script:contains(JSON.parse)")
            
            if not script_data:
                return self._parse_manga_details_html(soup, manga_id)
            
            json_match = re.search(r'JSON\.parse\(\s*"(.*)"\s*\)', script_data.string)
            if not json_match:
                return self._parse_manga_details_html(soup, manga_id)
            
            json_str = json_match.group(1)
            json_str = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), json_str)
            json_str = json_str.replace('\\"', '"').replace('\\\\', '\\')
            
            data = json.loads(json_str)
            return self._parse_manga_details_json(data, manga_id)
            
        except Exception as e:
            pass
            return {}

    def get_chapter(self, chapter_id: str) -> Chapter:
        chapter_data = self._get_pages(chapter_id)
        page_urls = [page.get("url", "") for page in chapter_data]
        manga_details = self.manga_details_request(chapter_id)
        
        return Chapter(
            title=manga_details.get("title", f"Gallery #{chapter_id}"),
            pages=page_urls,
            id=chapter_id
        )

    def _convert_to_manga(self, manga_dict: Dict[str, Any]) -> Manga:
        if not manga_dict:
            return None

        manga_id = manga_dict.get("id", "")
        
        title = manga_dict.get("title", "Unknown")
        author = manga_dict.get("author", manga_dict.get("artist", "Unknown"))
        description = manga_dict.get("description", "")
        poster = manga_dict.get("thumbnail_url", manga_dict.get("cover_url", ""))
        
        status = "Completed"
        genres = manga_dict.get("genres", "").split(", ") if isinstance(manga_dict.get("genres"), str) else []
        
        chapter_ids = {"Chapter 1": manga_id}

        return Manga(
            id=manga_id,
            url=f"{self.base_url}/g/{manga_id}/" if manga_id else "",
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

    def _build_search_query(self, query: str, filters: Dict[str, Any]) -> str:
        search_parts = [query] if query else []
        
        if self.language != "all" and self.language:
            search_parts.append(f"language:{self.language}")
        
        for filter_type in ["tag", "category", "artist", "group", "parody", "character"]:
            if filter_type in filters:
                tags = filters[filter_type].split(",")
                for tag in tags:
                    tag = tag.strip()
                    if tag:
                        prefix = "-" if tag.startswith("-") else ""
                        clean_tag = tag[1:] if prefix else tag
                        search_parts.append(f"{prefix}{filter_type}:\"{clean_tag}\"")
        
        if "pages" in filters and filters["pages"]:
            search_parts.append(f"pages:{filters['pages']}")
            
        if "uploaded" in filters and filters["uploaded"]:
            search_parts.append(f"uploaded:{filters['uploaded']}")
        
        return " ".join(search_parts)

    def _parse_search_results(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        results = []
        gallery_elements = soup.select(".gallery")
        
        for element in gallery_elements:
            try:
                url_element = element.select_one("a")
                if not url_element:
                    continue
                    
                relative_url = url_element.get("href", "")
                manga_id = relative_url.split("/")[-2] if relative_url else ""
                
                title_element = element.select_one(".caption")
                title = title_element.text.strip() if title_element else "Unknown Title"
                
                thumb_element = element.select_one(".cover img")
                thumbnail_url = None
                if thumb_element:
                    thumbnail_url = thumb_element.get("data-src") or thumb_element.get("src")
                
                if not self.preferences["display_full_title"]:
                    title = self._shorten_title(title)
                
                manga = {
                    "id": manga_id,
                    "title": title,
                    "url": relative_url,
                    "thumbnail_url": thumbnail_url,
                    "source": "nhentai"
                }
                results.append(manga)
                
            except Exception as e:
                pass
                continue
        
        return results

    def _shorten_title(self, title: str) -> str:
        pattern = r"(\[[^\]]*\]|\([^)]*\)|\{[^}]*\})"
        return re.sub(pattern, "", title).strip()

    def _parse_manga_details_json(self, data: Dict[str, Any], manga_id: str) -> Dict[str, Any]:
        titles = data.get("title", {})
        english_title = titles.get("english")
        japanese_title = titles.get("japanese")
        pretty_title = titles.get("pretty")
        
        if self.preferences["display_full_title"]:
            display_title = english_title or japanese_title or pretty_title or f"Gallery #{manga_id}"
        else:
            display_title = pretty_title or self._shorten_title(english_title or japanese_title or f"Gallery #{manga_id}")
        
        cover_url = None
        media_id = data.get("media_id", "")
        if media_id:
            cover_url = f"https://t.nhentai.net/galleries/{media_id}/cover.jpg"
        
        tags = data.get("tags", [])
        artist_tags = [tag.get("name") for tag in tags if tag.get("type") == "artist"]
        group_tags = [tag.get("name") for tag in tags if tag.get("type") == "group"]
        category_tags = [tag.get("name") for tag in tags if tag.get("type") == "category"]
        parody_tags = [tag.get("name") for tag in tags if tag.get("type") == "parody"]
        character_tags = [tag.get("name") for tag in tags if tag.get("type") == "character"]
        general_tags = [tag.get("name") for tag in tags if tag.get("type") == "tag"]
        
        manga_details = {
            "id": manga_id,
            "url": f"/g/{manga_id}/",
            "title": display_title,
            "cover_url": cover_url,
            "author": ", ".join(artist_tags),
            "artist": ", ".join(artist_tags),
            "groups": ", ".join(group_tags),
            "pages": len(data.get("images", {}).get("pages", [])),
            "favorites": data.get("num_favorites", 0),
            "upload_date": data.get("upload_date", 0),
            "description": "",
            "genres": ", ".join(general_tags),
            "parodies": ", ".join(parody_tags),
            "characters": ", ".join(character_tags),
            "categories": ", ".join(category_tags),
            "source": "nhentai",
            "_raw_data": data
        }
        
        description = f"Full English and Japanese titles:\n"
        if english_title:
            description += f"{english_title}\n"
        if japanese_title:
            description += f"{japanese_title}\n"
        
        description += f"\nPages: {manga_details['pages']}\n"
        description += f"Favorited by: {manga_details['favorites']}\n"
        
        if category_tags:
            description += f"\nCategories: {', '.join(category_tags)}\n"
        if parody_tags:
            description += f"Parodies: {', '.join(parody_tags)}\n"
        if character_tags:
            description += f"Characters: {', '.join(character_tags)}\n"
        
        manga_details["description"] = description
        
        return manga_details

    def _parse_manga_details_html(self, soup: BeautifulSoup, manga_id: str) -> Dict[str, Any]:
        try:
            title_element = soup.select_one("#info > h1")
            title = title_element.text.strip() if title_element else f"Gallery #{manga_id}"
            
            cover_element = soup.select_one("#cover > a > img")
            cover_url = cover_element.get("data-src") if cover_element else None
            
            tag_containers = soup.select("#tags > .tag-container")
            
            artist_tags = []
            group_tags = []
            category_tags = []
            parody_tags = []
            character_tags = []
            general_tags = []
            
            for container in tag_containers:
                tag_type_element = container.select_one(".tag-container > span.tags")
                if not tag_type_element:
                    continue
                    
                tag_type = tag_type_element.text.strip().lower()
                tags = [tag.text.strip() for tag in container.select("a.tag > span.name")]
                
                if "artist" in tag_type:
                    artist_tags = tags
                elif "group" in tag_type:
                    group_tags = tags
                elif "categor" in tag_type:
                    category_tags = tags
                elif "parody" in tag_type:
                    parody_tags = tags
                elif "character" in tag_type:
                    character_tags = tags
                elif "tag" in tag_type:
                    general_tags = tags
            
            pages_element = soup.select_one("#info > div")
            pages_text = pages_element.text if pages_element else ""
            pages_match = re.search(r'(\d+) pages', pages_text)
            pages = int(pages_match.group(1)) if pages_match else 0
            
            manga_details = {
                "id": manga_id,
                "url": f"/g/{manga_id}/",
                "title": title if self.preferences["display_full_title"] else self._shorten_title(title),
                "cover_url": cover_url,
                "author": ", ".join(artist_tags),
                "artist": ", ".join(artist_tags),
                "groups": ", ".join(group_tags),
                "pages": pages,
                "favorites": 0,
                "upload_date": 0,
                "description": "",
                "genres": ", ".join(general_tags),
                "parodies": ", ".join(parody_tags),
                "characters": ", ".join(character_tags),
                "categories": ", ".join(category_tags),
                "source": "nhentai"
            }
            
            description = f"Title: {title}\n\n"
            description += f"Pages: {pages}\n"
            
            if category_tags:
                description += f"\nCategories: {', '.join(category_tags)}\n"
            if parody_tags:
                description += f"Parodies: {', '.join(parody_tags)}\n"
            if character_tags:
                description += f"Characters: {', '.join(character_tags)}\n"
            
            manga_details["description"] = description
            
            return manga_details
            
        except Exception as e:
            pass
            return {
                "id": manga_id,
                "url": f"/g/{manga_id}/",
                "title": f"Gallery #{manga_id}",
                "description": "Error loading details",
                "source": "nhentai"
            }

    def _get_pages(self, chapter_id: str) -> List[Dict[str, Any]]:
        try:
            response = self.session.get(
                f"{self.base_url}/g/{chapter_id}/",
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            media_id = None
            pages_data = []
            
            media_server = self.preferences["media_server"]
            media_server_match = re.search(r'media_server\s*:\s*(\d+)', response.text)
            if media_server_match:
                media_server = int(media_server_match.group(1))
            
            script_data = None
            for script in soup.select("script"):
                if script.string and "JSON.parse" in script.string:
                    script_data = script
                    break
                    
            if script_data:
                json_match = re.search(r'JSON\.parse\(\s*"(.*)"\s*\)', script_data.string)
                if json_match:
                    json_str = json_match.group(1)
                    json_str = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), json_str)
                    json_str = json_str.replace('\\"', '"').replace('\\\\', '\\')
                    
                    try:
                        data = json.loads(json_str)
                        media_id = data.get("media_id", "")
                        
                        images = data.get("images", {})
                        pages = images.get("pages", [])
                        
                        for i, page in enumerate(pages):
                            page_type = page.get("t", "j")
                            extension = self.image_types.get(page_type, "jpg")
                            pages_data.append({
                                "index": i,
                                "url": f"https://i{media_server}.nhentai.net/galleries/{media_id}/{i + 1}.{extension}"
                            })
                    except Exception as e:
                        pass
            
            if not pages_data:
                
                thumb_element = soup.select_one("#cover img")
                if thumb_element:
                    thumb_url = thumb_element.get("data-src") or thumb_element.get("src") or ""
                    media_id_match = re.search(r'/galleries/(\d+)/', thumb_url)
                    if media_id_match:
                        media_id = media_id_match.group(1)
                
                if not media_id:
                    thumb_elements = soup.select(".gallerythumb img")
                    for element in thumb_elements:
                        thumb_url = element.get("data-src") or element.get("src") or ""
                        media_id_match = re.search(r'/galleries/(\d+)/', thumb_url)
                        if media_id_match:
                            media_id = media_id_match.group(1)
                            break
                
                pages_element = soup.select_one("#info > div")
                pages_text = pages_element.text if pages_element else ""
                pages_match = re.search(r'(\d+) pages', pages_text)
                page_count = int(pages_match.group(1)) if pages_match else 0
                
                if not page_count:
                    page_count = len(soup.select(".gallerythumb"))
                
                if media_id and page_count:
                    for i in range(page_count):
                        pages_data.append({
                            "index": i,
                            "url": f"https://i{media_server}.nhentai.net/galleries/{media_id}/{i + 1}.jpg"
                        })
                        
                if not pages_data:
                    img_elements = soup.select("#image-container img")
                    for i, img in enumerate(img_elements):
                        img_url = img.get("src") or img.get("data-src") or ""
                        if img_url:
                            pages_data.append({
                                "index": i,
                                "url": img_url
                            })
            
            return pages_data
            
        except Exception as e:
            pass
            return []

    def _get_filters(self) -> Dict[str, Any]:
        return {
            "sort_options": [
                {"name": "Recent", "value": "date"},
                {"name": "Popular: All Time", "value": "popular"},
                {"name": "Popular: Month", "value": "popular-month"},
                {"name": "Popular: Week", "value": "popular-week"},
                {"name": "Popular: Today", "value": "popular-today"}
            ],
            "category_suggestions": [
                "doujinshi", "manga", "artistcg", "gamecg", "western",
                "non-h", "imageset", "cosplay", "asianporn", "misc"
            ],
            "tag_suggestions": [
                "anal", "big breasts", "sole female", "sole male", "group",
                "nakadashi", "blowjob", "ahegao", "incest", "futanari",
                "shotacon", "lolicon", "femdom", "yaoi", "yuri",
                "monster", "netorare", "monster girl", "tentacles"
            ]
        }
