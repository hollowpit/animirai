
import json
import re
import time
import urllib.parse
import requests
import cloudscraper
from typing import List, Dict, Any, Optional
from datetime import datetime
from src.lib.types import Scraper, Manga

class Comick(Scraper):
    def __init__(self):
        super().__init__(
            name="Comick",
            url="https://comick.io",
            api_url="https://api.comick.fun",
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
            "Referer": f"{self.base_url}/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": self.base_url,
            "Connection": "keep-alive",
            "sec-ch-ua": '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"'
        }
        self.preferences = {
            "ignored_groups": set(),
            "ignored_tags": "",
            "show_alternative_titles": False,
            "include_mu_tags": False,
            "group_tags": False,
            "update_cover": True,
            "local_title": False,
            "score_position": "top"
        }
        self.search_results = []
        self.chapters_limit = 99999

    def popular_manga_request(self, page: int = 1) -> List[Dict[str, Any]]:
        filters = {"sort": "follow"}
        return self._search_manga_request(page=page, query="", filters=filters)

    def popular_manga(self, page: int = 1) -> List[Manga]:
        manga_list = self.popular_manga_request(page)
        return [self._convert_to_manga(manga) for manga in manga_list]

    def latest_manga_request(self, page: int = 1) -> List[Dict[str, Any]]:
        filters = {"sort": "uploaded"}
        return self._search_manga_request(page=page, query="", filters=filters)

    def latest_manga(self, page: int = 1) -> List[Manga]:
        manga_list = self.latest_manga_request(page)
        return [self._convert_to_manga(manga) for manga in manga_list]

    def search_manga_request(self, query: str, page: int = 1, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        return self._search_manga_request(query, page, filters)

    def search_manga(self, query: str, page: int = 1, filters: Optional[Dict[str, Any]] = None) -> List[Manga]:
        manga_list = self.search_manga_request(query, page, filters)
        return [self._convert_to_manga(manga) for manga in manga_list]

    def manga_details_request(self, manga_id: str) -> Dict[str, Any]:
        manga = {"url": f"/comic/{manga_id}#"}
        return self._get_manga_details(manga)

    def manga_details(self, manga_id: str) -> Manga:
        manga_dict = self.manga_details_request(manga_id)
        return self._convert_to_manga(manga_dict, with_chapters=True)

    def _convert_to_manga(self, manga_dict: Dict[str, Any], with_chapters: bool = False) -> Manga:
        if not manga_dict:
            return None

        title = manga_dict.get("title", "Unknown")
        author = manga_dict.get("author", "Unknown")
        description = manga_dict.get("description", "")
        poster = manga_dict.get("thumbnail_url", "")
        
        manga_id = manga_dict.get("id", "")
        status = manga_dict.get("status", "Ongoing")
        genres = manga_dict.get("genres", [])
        
        chapter_and_pages = {}
        
        if with_chapters:
            chapter_list = self._get_chapters(manga_dict)
            chapter_and_pages = {"chapters": []}
            
            for chapter in chapter_list:
                pages = self._get_pages(chapter)
                page_urls = [page.get("url", "") for page in pages]
                
                chapter_and_pages["chapters"].append({
                    "title": chapter.get("name", f"Chapter {chapter.get('chapter_number', '?')}"),
                    "total_pages": len(pages),
                    "pages": page_urls
                })
        
        return Manga(
            title=title,
            author=author,
            description=description,
            poster=poster,
            chapters=len(chapter_and_pages.get("chapters", [])) if with_chapters else 0,
            chapter_and_pages=chapter_and_pages,
            tags=genres,
            genres=genres,
            status=status
        )

    def _search_manga_request(self, query: str, page: int = 1, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        filters = filters or {}
        
        if query.startswith("id:"):
            slug_or_hid = query[3:]
            manga_details = self._get_manga_details({"url": f"/comic/{slug_or_hid}#"})
            return [manga_details] if manga_details else []
        
        if query:
            url = f"{self.api_url}/v1.0/search"
            params = {
                "q": query.strip(),
                "limit": 300,
                "page": 1,
                "tachiyomi": "true"
            }
            
            response = self._make_request(url, params=params)
            if not response:
                return []
            
            manga_list = []
            for item in response:
                manga = {
                    "id": item.get("hid", ""),
                    "title": item.get("title", "Unknown"),
                    "url": f"/comic/{item.get('hid')}#", 
                    "thumbnail_url": self._parse_cover(item.get("cover_url"), item.get("md_covers", []))
                }
                manga_list.append(manga)
            
            return manga_list
        
        url = f"{self.api_url}/v1.0/search"
        params = {
            "limit": 300,
            "page": 1,
            "tachiyomi": "true"
        }
        
        self._apply_filters(params, filters)
        
        if self.preferences["ignored_tags"]:
            ignored_tags = self.preferences["ignored_tags"].split(",")
            for tag in ignored_tags:
                if tag.strip():
                    params.setdefault("excluded-tags", []).append(self._format_tag(tag.strip()))
        
        all_results = []
        current_page = 1
        has_next_page = True
        
        while has_next_page and current_page <= 5:
            params["page"] = current_page
            response = self._make_request(url, params=params)
            
            if not response or len(response) == 0:
                has_next_page = False
                break
                
            for item in response:
                manga = {
                    "id": item.get("hid", ""),
                    "title": item.get("title", "Unknown"),
                    "url": f"/comic/{item.get('hid')}#", 
                    "thumbnail_url": self._parse_cover(item.get("cover_url"), item.get("md_covers", [])),
                    "description": item.get("desc", ""),
                    "status": self._parse_status(item.get("status"), item.get("translation_completed"))
                }
                all_results.append(manga)
            
            if len(response) < params["limit"]:
                has_next_page = False
            else:
                current_page += 1
        
        return all_results

    def _get_manga_details(self, manga: Dict[str, Any]) -> Dict[str, Any]:
        if not manga['url'].endswith("#"):
            return {}
        
        manga_url = manga['url'].rstrip("#")
        url = f"{self.api_url}{manga_url}"
        params = {"tachiyomi": "true"}
        
        response = self._make_request(url, params=params)
        if not response:
            return {}
        
        comic_data = response.get("comic", {})
        authors_data = response.get("authors", [])
        artists_data = response.get("artists", [])
        genres_data = response.get("genres", [])
        demographic = response.get("demographic")
        
        title_lang = self.lang.lower() if self.preferences["local_title"] else "all"
        
        alt_titles = comic_data.get("md_titles", [])
        entry_title = comic_data.get("title", "Unknown")
        
        for alt in alt_titles:
            if (title_lang != "all" and 
                alt.get("lang") and 
                title_lang.startswith(alt.get("lang")) and
                alt.get("title")):
                entry_title = alt["title"]
                break
        
        cover_url = comic_data.get("cover_url")
        md_covers = comic_data.get("md_covers", [])
        
        if not self.preferences["update_cover"] and manga.get("thumbnail_url") != cover_url:
            covers_url = f"{self.api_url}/comic/{comic_data.get('slug') or comic_data.get('hid')}/covers"
            covers_params = {"tachiyomi": "true"}
            covers_response = self._make_request(covers_url, params=covers_params)
            
            if covers_response:
                all_covers = covers_response.get("md_covers", [])[::-1]
                first_vol_covers = [c for c in all_covers if c.get("vol") == "1"]
                if not first_vol_covers:
                    first_vol_covers = all_covers
                
                iso_lang = comic_data.get("iso639_1", "")
                original_covers = [c for c in first_vol_covers if iso_lang and iso_lang.startswith(c.get("locale", ""))]
                local_covers = [c for c in first_vol_covers if self.lang.startswith(c.get("locale", ""))]
                
                selected_covers = local_covers or original_covers or first_vol_covers
                md_covers = selected_covers
        
        score_position = self.preferences["score_position"]
        description = ""
        
        fancy_score = ""
        if comic_data.get("bayesian_rating"):
            score = float(comic_data["bayesian_rating"])
            stars = round(score / 2)
            fancy_score = "★" * stars + "☆" * (5 - stars) + f" {score}"
        
        if score_position == "top" and fancy_score:
            description += fancy_score
        
        if comic_data.get("desc"):
            desc = self._beautify_description(comic_data["desc"])
            if description:
                description += "\n\n"
            description += desc
        
        if score_position == "middle" and fancy_score:
            if description:
                description += "\n\n"
            description += fancy_score
        
        if self.preferences["show_alternative_titles"] and alt_titles:
            all_titles = [{"title": comic_data.get("title")}] + alt_titles
            alt_title_list = []
            
            for title in all_titles:
                if title.get("title") and title.get("title") != entry_title:
                    alt_title_list.append(f"• {title['title']}")
            
            if alt_title_list:
                if description:
                    description += "\n\n"
                description += "Alternative Titles:\n" + "\n".join(alt_title_list)
        
        if score_position == "bottom" and fancy_score:
            if description:
                description += "\n\n"
            description += fancy_score
        
        status = self._parse_status(comic_data.get("status"), comic_data.get("translation_completed"))
        
        genres = []
        
        country = comic_data.get("country")
        if country == "jp":
            genres.append({"group": "Origination", "name": "Manga"})
        elif country == "kr":
            genres.append({"group": "Origination", "name": "Manhwa"})
        elif country == "cn":
            genres.append({"group": "Origination", "name": "Manhua"})
        
        if demographic:
            genres.append({"group": "Demographic", "name": demographic})
        
        md_genres = comic_data.get("md_comic_md_genres", [])
        for genre in md_genres:
            md_genre = genre.get("md_genres")
            if md_genre and md_genre.get("name"):
                genres.append({
                    "group": md_genre.get("group", ""),
                    "name": md_genre.get("name", "")
                })
        
        for genre in genres_data:
            if genre.get("name"):
                genres.append({
                    "group": genre.get("group", ""),
                    "name": genre.get("name", "")
                })
        
        if self.preferences["include_mu_tags"]:
            mu_comics = comic_data.get("mu_comics", {})
            mu_categories = mu_comics.get("mu_comic_categories", [])
            
            for category in mu_categories:
                if category and category.get("mu_categories") and category["mu_categories"].get("title"):
                    genres.append({
                        "group": "Category",
                        "name": category["mu_categories"]["title"]
                    })
        
        formatted_genres = []
        genres = [g for g in genres if g.get("name") and g.get("group")]
        genres.sort(key=lambda x: (x.get("name", ""), x.get("group", "")))
        
        for genre in genres:
            if self.preferences["group_tags"]:
                formatted_genres.append(f"{genre['group']}:{genre['name'].strip()}")
            else:
                formatted_genres.append(genre['name'].strip())
        
        formatted_genres = list(dict.fromkeys(formatted_genres))
        
        authors = [a.get("name", "").strip() for a in authors_data if a.get("name")]
        artists = [a.get("name", "").strip() for a in artists_data if a.get("name")]
        
        result = {
            "id": comic_data.get("hid", ""),
            "url": manga_url + "#",
            "title": entry_title,
            "author": ", ".join(authors),
            "artist": ", ".join(artists),
            "description": description,
            "genres": formatted_genres,
            "status": status,
            "thumbnail_url": self._parse_cover(cover_url, md_covers),
            "hid": comic_data.get("hid", ""),
            "slug": comic_data.get("slug"),
        }
        
        return result

    def _get_chapters(self, manga: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not manga['url'].endswith("#"):
            return []
        
        manga_url = manga['url'].rstrip("#")
        url = f"{self.api_url}{manga_url}/chapters"
        
        params = {
            "tachiyomi": "true",
            "limit": str(self.chapters_limit)
        }
        
        if self.lang != "all":
            params["lang"] = self.lang
        
        response = self._make_request(url, params=params)
        if not response:
            return []
        
        chapters_data = response.get("chapters", [])
        current_timestamp = int(time.time() * 1000)
        
        chapters = []
        for chapter in chapters_data:
            publish_time = self._parse_date(chapter.get("publish_at", ""))
            if publish_time > current_timestamp:
                continue
            
            chapter_groups = [g.lower() for g in chapter.get("group_name", [])]
            if any(g in self.preferences["ignored_groups"] for g in chapter_groups):
                continue
            
            chap_str = chapter.get("chap", "0")
            vol_str = chapter.get("vol", "0")
            
            chap_is_digit = False
            if chap_str is not None:
                chap_is_digit = chap_str.replace(".", "", 1).isdigit()
            
            vol_is_digit = False
            if vol_str is not None:
                vol_is_digit = vol_str.replace(".", "", 1).isdigit()
            
            chapter_data = {
                "id": chapter.get("hid", ""),
                "url": f"{manga_url}/{chapter.get('hid', '')}-chapter-{chap_str or ''}-{chapter.get('lang', '')}",
                "name": self._beautify_chapter_name(
                    vol_str or "",
                    chap_str or "",
                    chapter.get("title", "")
                ),
                "uploaded": self._parse_date(chapter.get("created_at", "")),
                "scanlator": ", ".join(chapter.get("group_name", [])) or "Unknown",
                "chapter_number": float(chap_str) if chap_is_digit else 0,
                "volume": float(vol_str) if vol_is_digit else None,
            }
            
            chapters.append(chapter_data)
        
        chapters.sort(key=lambda x: (x.get("volume", 0) or 0, x.get("chapter_number", 0) or 0), reverse=True)
        
        return chapters

    def _get_pages(self, chapter: Dict[str, Any]) -> List[Dict[str, Any]]:
        if isinstance(chapter, dict):
            chapter_hid = chapter["url"].split("/")[-1].split("-")[0]
        else:
            chapter_hid = chapter
            
        url = f"{self.api_url}/chapter/{chapter_hid}"
        params = {"tachiyomi": "true"}
        
        response = self._make_request(url, params=params)
        if not response:
            return []
        
        chapter_data = response.get("chapter", {})
        images = chapter_data.get("images", [])
        
        if not images:
            params["_"] = str(int(time.time() * 1000))
            response = self._make_request(url, params=params)
            if response:
                chapter_data = response.get("chapter", {})
                images = chapter_data.get("images", [])
        
        pages = []
        for i, img in enumerate(images):
            if img.get("url"):
                pages.append({
                    "index": i,
                    "url": img["url"]
                })
        
        return pages

    def _make_request(self, url: str, params: Optional[Dict[str, Any]] = None, method: str = "GET", retries: int = 3) -> Any:
        try:
            if method == "GET" and params:
                query_params = []
                for key, value in params.items():
                    if isinstance(value, list):
                        for item in value:
                            query_params.append((key, item))
                    else:
                        query_params.append((key, value))
                
                url_parts = list(urllib.parse.urlparse(url))
                query = urllib.parse.urlencode(query_params, doseq=True)
                url_parts[4] = query
                url = urllib.parse.urlunparse(url_parts)
                params = None
            
            last_error = None
            for attempt in range(retries):
                try:
                    response = self.session.request(
                        method,
                        url,
                        params=params,
                        headers=self.headers,
                        timeout=30
                    )
                    response.raise_for_status()
                    
                    data = response.json()
                    
                    if isinstance(data, dict) and "statusCode" in data and "message" in data:
                        return None
                    
                    return data
                    
                except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
                    last_error = e
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
            
            return None
            
        except Exception:
            return None

    def _apply_filters(self, params: Dict[str, Any], filters: Dict[str, Any]):
        if "sort" in filters:
            params["sort"] = filters["sort"]
        
        if "country" in filters:
            params["country"] = filters["country"]
        
        if "demographic" in filters:
            params["demographic"] = filters["demographic"]
        
        if "status" in filters:
            params["status"] = filters["status"]
        
        if "content_rating" in filters:
            params["content_rating"] = filters["content_rating"]
        
        if "completed" in filters and filters["completed"]:
            params["completed"] = "true"
        
        if "time" in filters:
            params["time"] = filters["time"]
        
        if "minimum" in filters:
            params["minimum"] = filters["minimum"]
        
        if "from" in filters:
            params["from"] = filters["from"]
            
        if "to" in filters:
            params["to"] = filters["to"]
        
        if "genres" in filters:
            params["genres"] = filters["genres"]
        
        if "excludes" in filters:
            params["excludes"] = filters["excludes"]
        
        if "tags" in filters:
            for tag in filters["tags"].split(","):
                tag = tag.strip()
                if tag:
                    params.setdefault("tags", []).append(self._format_tag(tag))
        
        if "excluded_tags" in filters:
            for tag in filters["excluded_tags"].split(","):
                tag = tag.strip()
                if tag:
                    params.setdefault("excluded-tags", []).append(self._format_tag(tag))

    def _format_tag(self, tag: str) -> str:
        formatted = tag.lower().replace(" ", "-").replace("/", "-")
        formatted = formatted.replace("'-", "-and-039-").replace("'", "-and-039-")
        return formatted

    def _parse_cover(self, thumbnail_url: Optional[str], md_covers: List[Dict[str, Any]]) -> Optional[str]:
        b2key = None
        vol = ""
        
        for cover in md_covers:
            if cover.get("b2key"):
                b2key = cover["b2key"]
                vol = cover.get("vol", "")
                break
        
        if not b2key or not thumbnail_url:
            return thumbnail_url
        
        return f"{thumbnail_url.rsplit('/', 1)[0]}/{b2key}#{vol}"

    def _beautify_description(self, description: str) -> str:
        description = description.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
        
        if "---" in description:
            description = description.split("---")[0]
        
        description = re.sub(r'\[([^]]+)]\(([^)]+)\)', r'\1', description)
        description = re.sub(r'\*+\s*([^*]*)\s*\*+', r'\1', description)
        description = re.sub(r'_+\s*([^_]*)\s*_+', r'\1', description)
        
        return description.strip()

    def _parse_status(self, status: Optional[int], translation_complete: Optional[bool]) -> str:
        if status == 1:
            return "Ongoing"
        elif status == 2:
            if translation_complete:
                return "Completed"
            else:
                return "Publication Complete"
        elif status == 3:
            return "Cancelled"
        elif status == 4:
            return "On Hiatus"
        else:
            return "Unknown"

    def _beautify_chapter_name(self, vol: str, chap: str, title: str) -> str:
        result = []
        
        if vol:
            if not chap:
                result.append(f"Volume {vol}")
            else:
                result.append(f"Vol. {vol}")
        
        if chap:
            if not vol:
                result.append(f"Chapter {chap}")
            else:
                result.append(f"Ch. {chap}")
        
        if title:
            if not chap:
                result.append(title)
            else:
                result.append(f": {title}")
        
        return "".join(result)

    def _parse_date(self, date_string: str) -> int:
        if not date_string:
            return 0
        
        try:
            dt_format = "%Y-%m-%dT%H:%M:%S.%fZ"
            if "." not in date_string:
                dt_format = "%Y-%m-%dT%H:%M:%SZ"
            
            dt = datetime.strptime(date_string, dt_format)
            return int(dt.timestamp() * 1000)
        except Exception:
            return 0

    def _get_filters(self) -> Dict[str, Any]:
        return {
            "genres": self._get_genres_list(),
            "demographics": self._get_demographic_list(),
            "types": self._get_type_list(),
            "created_at": self._get_created_at_list(),
            "sorts": self._get_sorts_list(),
            "statuses": self._get_status_list(),
            "content_ratings": self._get_content_rating_list(),
        }

    def _get_genres_list(self) -> List[Dict[str, str]]:
        return [
            {"title": "4-Koma", "value": "4-koma"},
            {"title": "Action", "value": "action"},
            {"title": "Adaptation", "value": "adaptation"},
            {"title": "Adult", "value": "adult"},
            {"title": "Adventure", "value": "adventure"},
            {"title": "Aliens", "value": "aliens"},
            {"title": "Animals", "value": "animals"},
            {"title": "Anthology", "value": "anthology"},
            {"title": "Award Winning", "value": "award-winning"},
            {"title": "Comedy", "value": "comedy"},
            {"title": "Cooking", "value": "cooking"},
            {"title": "Crime", "value": "crime"},
            {"title": "Crossdressing", "value": "crossdressing"},
            {"title": "Delinquents", "value": "delinquents"},
            {"title": "Demons", "value": "demons"},
            {"title": "Doujinshi", "value": "doujinshi"},
            {"title": "Drama", "value": "drama"},
            {"title": "Ecchi", "value": "ecchi"},
            {"title": "Fan Colored", "value": "fan-colored"},
            {"title": "Fantasy", "value": "fantasy"},
            {"title": "Full Color", "value": "full-color"},
            {"title": "Gender Bender", "value": "gender-bender"},
            {"title": "Genderswap", "value": "genderswap"},
            {"title": "Ghosts", "value": "ghosts"},
            {"title": "Gore", "value": "gore"},
            {"title": "Gyaru", "value": "gyaru"},
            {"title": "Harem", "value": "harem"},
            {"title": "Historical", "value": "historical"},
            {"title": "Horror", "value": "horror"},
            {"title": "Incest", "value": "incest"},
            {"title": "Isekai", "value": "isekai"},
            {"title": "Loli", "value": "loli"},
            {"title": "Long Strip", "value": "long-strip"},
            {"title": "Mafia", "value": "mafia"},
            {"title": "Magic", "value": "magic"},
            {"title": "Magical Girls", "value": "magical-girls"},
            {"title": "Martial Arts", "value": "martial-arts"},
            {"title": "Mature", "value": "mature"},
            {"title": "Mecha", "value": "mecha"},
            {"title": "Medical", "value": "medical"},
            {"title": "Military", "value": "military"},
            {"title": "Monster Girls", "value": "monster-girls"},
            {"title": "Monsters", "value": "monsters"},
            {"title": "Music", "value": "music"},
            {"title": "Mystery", "value": "mystery"},
            {"title": "Ninja", "value": "ninja"},
            {"title": "Office Workers", "value": "office-workers"},
            {"title": "Official Colored", "value": "official-colored"},
            {"title": "Oneshot", "value": "oneshot"},
            {"title": "Philosophical", "value": "philosophical"},
            {"title": "Police", "value": "police"},
            {"title": "Post-Apocalyptic", "value": "post-apocalyptic"},
            {"title": "Psychological", "value": "psychological"},
            {"title": "Reincarnation", "value": "reincarnation"},
            {"title": "Reverse Harem", "value": "reverse-harem"},
            {"title": "Romance", "value": "romance"},
            {"title": "Samurai", "value": "samurai"},
            {"title": "School Life", "value": "school-life"},
            {"title": "Sci-Fi", "value": "sci-fi"},
            {"title": "Sexual Violence", "value": "sexual-violence"},
            {"title": "Shota", "value": "shota"},
            {"title": "Shoujo Ai", "value": "shoujo-ai"},
            {"title": "Shounen Ai", "value": "shounen-ai"},
            {"title": "Slice of Life", "value": "slice-of-life"},
            {"title": "Smut", "value": "smut"},
            {"title": "Sports", "value": "sports"},
            {"title": "Superhero", "value": "superhero"},
            {"title": "Supernatural", "value": "supernatural"},
            {"title": "Survival", "value": "survival"},
            {"title": "Thriller", "value": "thriller"},
            {"title": "Time Travel", "value": "time-travel"},
            {"title": "Traditional Games", "value": "traditional-games"},
            {"title": "Tragedy", "value": "tragedy"},
            {"title": "User Created", "value": "user-created"},
            {"title": "Vampires", "value": "vampires"},
            {"title": "Video Games", "value": "video-games"},
            {"title": "Villainess", "value": "villainess"},
            {"title": "Virtual Reality", "value": "virtual-reality"},
            {"title": "Web Comic", "value": "web-comic"},
            {"title": "Wuxia", "value": "wuxia"},
            {"title": "Yaoi", "value": "yaoi"},
            {"title": "Yuri", "value": "yuri"},
            {"title": "Zombies", "value": "zombies"},
        ]

    def _get_demographic_list(self) -> List[Dict[str, str]]:
        return [
            {"title": "Shounen", "value": "1"},
            {"title": "Shoujo", "value": "2"},
            {"title": "Seinen", "value": "3"},
            {"title": "Josei", "value": "4"},
            {"title": "None", "value": "5"},
        ]

    def _get_type_list(self) -> List[Dict[str, str]]:
        return [
            {"title": "Manga", "value": "jp"},
            {"title": "Manhwa", "value": "kr"},
            {"title": "Manhua", "value": "cn"},
            {"title": "Others", "value": "others"},
        ]

    def _get_created_at_list(self) -> List[Dict[str, str]]:
        return [
            {"title": "Any time", "value": ""},
            {"title": "3 days", "value": "3"},
            {"title": "7 days", "value": "7"},
            {"title": "30 days", "value": "30"},
            {"title": "3 months", "value": "90"},
            {"title": "6 months", "value": "180"},
            {"title": "1 year", "value": "365"},
        ]

    def _get_sorts_list(self) -> List[Dict[str, str]]:
        return [
            {"title": "Most popular", "value": "follow"},
            {"title": "Most follows", "value": "user_follow_count"},
            {"title": "Most views", "value": "view"},
            {"title": "High rating", "value": "rating"},
            {"title": "Last updated", "value": "uploaded"},
            {"title": "Newest", "value": "created_at"},
        ]

    def _get_status_list(self) -> List[Dict[str, str]]:
        return [
            {"title": "All", "value": "0"},
            {"title": "Ongoing", "value": "1"},
            {"title": "Completed", "value": "2"},
            {"title": "Cancelled", "value": "3"},
            {"title": "Hiatus", "value": "4"},
        ]

    def _get_content_rating_list(self) -> List[Dict[str, str]]:
        return [
            {"title": "All", "value": ""},
            {"title": "Safe", "value": "safe"},
            {"title": "Suggestive", "value": "suggestive"},
            {"title": "Erotica", "value": "erotica"},
        ]
