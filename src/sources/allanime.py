import json
import re
import time
import requests
import cloudscraper
from typing import List, Dict, Any, Optional
from datetime import datetime
from urllib.parse import urlparse
from src.lib.types import Scraper, Anime, Episode

class AllAnime(Scraper):
    def __init__(self):
        super().__init__(
            name="AllAnime",
            url="https://allanime.to",
            api_url="https://api.allanime.day",
            scraper_version="1.0.0"
        )
        self.available_filters = self._get_filters()
        self.session = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False
            }
        )
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/"
        }
        self.preferences = {
            "preferred_quality": "1080p",
            "preferred_sub": "sub",
            "preferred_title_style": "romaji",
            "preferred_server": "site_default",
            "hoster_selection": {"default", "ac", "ak", "kir", "luf-mp4", "si-hls", "s-mp4", "ac-hls"},
            "alt_hoster_selection": {"player", "vidstreaming", "okru", "mp4upload", "streamlare", "doodstream", "filemoon", "streamwish"}
        }
        self.page_size = 26
        self.available_qualities = ["1080p", "720p", "480p", "360p", "240p"]

        # GraphQL queries
        self.search_query = "query ($search: SearchInput, $limit: Int, $page: Int, $translationType: VaildTranslationTypeEnumType, $countryOrigin: VaildCountryOriginEnumType) { shows(search: $search, limit: $limit, page: $page, translationType: $translationType, countryOrigin: $countryOrigin) { edges { _id name englishName nativeName thumbnail slugTime type season score availableEpisodesDetail } } }"
        self.details_query = "query ($_id: String!) { show(_id: $_id) { _id name englishName nativeName thumbnail description genres studios season status score type availableEpisodesDetail } }"
        self.episodes_query = "query ($_id: String!) { show(_id: $_id) { _id availableEpisodesDetail } }"
        self.streams_query = "query ($showId: String!, $translationType: VaildTranslationTypeEnumType!, $episodeString: String!) { episode(showId: $showId, translationType: $translationType, episodeString: $episodeString) { sourceUrls } }"

    def popular_anime(self, page: int = 1) -> List[Anime]:
        try:
            # Use a different query approach for popular anime
            data = {
                "variables": {
                    "search": {
                        "allowAdult": False,
                        "allowUnknown": False,
                        "sortBy": "Top" # Sort by top rating
                    },
                    "limit": self.page_size,
                    "page": page,
                    "translationType": self.preferences["preferred_sub"],
                    "countryOrigin": "ALL"
                },
                "query": self.search_query
            }

            response = self.session.post(
                f"{self.api_url}/api",
                json=data,
                headers=self.headers
            )

            if response.status_code != 200:
                print(f"Error: API returned status code {response.status_code}")
                print(f"Response: {response.text[:200]}")
                return []

            data = response.json()
            shows = data.get('data', {}).get('shows', {})
            edges = shows.get('edges', [])

            if not edges:
                print("No popular anime found in API response")
                return []

            results = []
            for item in edges:
                if not item or '_id' not in item:
                    continue

                title = item.get('name', 'Unknown Title')
                if self.preferences["preferred_title_style"] == "eng":
                    title = item.get('englishName') or title
                elif self.preferences["preferred_title_style"] == "native":
                    title = item.get('nativeName') or title

                thumbnail_url = item.get('thumbnail')
                url = f"{self.base_url}/anime/{self._slugify(title)}"
                anime_id = item.get('_id')

                episodes_detail = item.get('availableEpisodesDetail', {})
                episode_count = 0
                episode_ids = {}

                if isinstance(episodes_detail, dict):
                    sub_episodes = episodes_detail.get(self.preferences["preferred_sub"], [])
                    episode_count = len(sub_episodes)

                    # Create episode IDs dictionary
                    for i, ep_str in enumerate(sub_episodes):
                        episode_ids[f"Episode {ep_str}"] = f"{anime_id}-{ep_str}"

                if episode_count == 0:
                    # Default to at least one episode if none found
                    episode_count = 1
                    episode_ids = {"Episode 1": anime_id}

                anime = Anime(
                    id=anime_id,
                    title=title,
                    url=url,
                    description="",
                    poster=thumbnail_url,
                    episodes=episode_count,
                    episode_ids=episode_ids,
                    tags=[],
                    genres=[],
                    status="Ongoing",
                    author=""
                )

                results.append(anime)

            return results

        except Exception as e:
            print(f"Error fetching popular anime: {e}")
            import traceback
            traceback.print_exc()
            return []

    def latest_anime(self, page: int = 1) -> List[Anime]:
        """
        Returns an empty list as this functionality is not implemented.
        """
        return []

    def search_anime(self, query: str, page: int = 1, filters: Optional[Dict[str, Any]] = None) -> List[Anime]:
        try:
            variables = {
                "search": {
                    "allowAdult": False,
                    "allowUnknown": False
                },
                "limit": self.page_size,
                "page": page,
                "translationType": self.preferences["preferred_sub"],
                "countryOrigin": "ALL"
            }

            if query:
                variables["search"]["query"] = query

            if filters:
                if "origin" in filters:
                    variables["countryOrigin"] = filters["origin"]

                if "season" in filters and "year" in filters:
                    variables["search"]["season"] = {
                        "quarter": filters["season"],
                        "year": int(filters["year"])
                    }

                if "genre" in filters:
                    variables["search"]["genres"] = [filters["genre"]]

                if "type" in filters:
                    variables["search"]["types"] = [filters["type"]]

                if "sortBy" in filters:
                    variables["search"]["sortBy"] = filters["sortBy"]

            data = {
                "variables": variables,
                "query": self.search_query
            }

            response = self.session.post(
                f"{self.api_url}/api",
                json=data,
                headers=self.headers
            )

            if response.status_code != 200:
                return []

            data = response.json()
            shows = data.get('data', {}).get('shows', {})
            edges = shows.get('edges', [])

            results = []
            for item in edges:
                if not item or '_id' not in item:
                    continue

                title = item.get('name', 'Unknown Title')
                if self.preferences["preferred_title_style"] == "eng":
                    title = item.get('englishName') or title
                elif self.preferences["preferred_title_style"] == "native":
                    title = item.get('nativeName') or title

                thumbnail_url = item.get('thumbnail')
                anime_id = f"{item.get('_id')}<&sep>{item.get('slugTime', '')}<&sep>{self._slugify(item.get('name', ''))}"

                episodes_detail = item.get('availableEpisodesDetail', {})
                episode_count = 0

                if isinstance(episodes_detail, dict):
                    sub_episodes = episodes_detail.get(self.preferences["preferred_sub"], [])
                    episode_count = len(sub_episodes)

                url = f"{self.base_url}/anime/{self._slugify(title)}"
                anime_id = item.get('_id')
                
                anime = Anime(
                    id=anime_id,
                    url=url,
                    title=title,
                    description="",
                    poster=thumbnail_url,
                    episodes=episode_count,
                    episode_ids={},
                    tags=[],
                    genres=[],
                    status="Ongoing",
                    author=""
                )

                results.append(anime)

            return results

        except Exception as e:
            print(f"Error searching anime: {e}")
            return []

    def get_anime(self, anime_id: str) -> Anime:
        try:
            real_id = anime_id.split("<&sep>")[0]

            data = {
                "variables": {
                    "_id": real_id
                },
                "query": self.details_query
            }

            response = self.session.post(
                f"{self.api_url}/api",
                json=data,
                headers=self.headers
            )

            if response.status_code != 200:
                return None

            data = response.json()
            show = data.get('data', {}).get('show')

            if not show:
                return None

            title = show.get('name', 'Unknown Title')
            if self.preferences["preferred_title_style"] == "eng":
                title = show.get('englishName') or title
            elif self.preferences["preferred_title_style"] == "native":
                title = show.get('nativeName') or title

            genres = show.get('genres', [])
            status = self._parse_status(show.get('status'))

            description_raw = show.get('description', '')
            description = 'No description available'
            if description_raw:
                temp_desc = description_raw.replace('<br>', '\n').replace('<br/>', '\n')
                description = re.sub(r'<[^>]+>', '', temp_desc).strip()

            available_episodes = show.get('availableEpisodesDetail', {})
            episode_ids = {}

            if isinstance(available_episodes, dict):
                sub_pref = self.preferences["preferred_sub"]
                episode_list = available_episodes.get(sub_pref, [])

                for i, ep_str in enumerate(episode_list):
                    payload = {
                        "variables": {
                            "showId": real_id,
                            "translationType": sub_pref,
                            "episodeString": ep_str
                        },
                        "query": self.streams_query
                    }
                    episode_ids[f"Episode {ep_str}"] = json.dumps(payload)

            return Anime(
                id="missing",
                url="missing",
                author="missing",
                title=title,
                description=description,
                poster=show.get('thumbnail'),
                episodes=len(episode_ids),
                episode_ids=episode_ids,
                tags=genres,
                genres=genres,
                status=status
            )

        except Exception as e:
            print(f"Error fetching anime details: {e}")
            return None

    def get_episode(self, episode_id: str) -> Episode:
        try:
            data = json.loads(episode_id)

            # Make sure we have the right headers for API call
            api_headers = self.headers.copy()
            api_headers['Host'] = urllib.parse.urlparse(self.api_url).netloc

            response = self.session.post(
                f"{self.api_url}/api",
                json=data,
                headers=api_headers
            )

            if response.status_code != 200:
                print(f"Error fetching episode: Status code {response.status_code}")
                return Episode(
                    id=episode_id,
                    title="Error",
                    url="",
                    quality="unknown",
                    language="unknown"
                )

            response_data = response.json()

            episode_data = response_data.get('data', {}).get('episode', {})
            if not episode_data or 'sourceUrls' not in episode_data:
                print("No streams found in episode data")
                return Episode(
                    id=episode_id,
                    title="No streams found",
                    url="",
                    quality="unknown",
                    language="unknown"
                )

            raw_sources = episode_data.get('sourceUrls', [])
            if not raw_sources:
                print("Empty sourceUrls in episode data")
                return Episode(
                    id=episode_id,
                    title="No sources found",
                    url="",
                    quality="unknown",
                    language="unknown"
                )

            # Extract variables to use in the Episode object
            variables = data.get('variables', {})
            episode_string = variables.get('episodeString', 'unknown')
            language = variables.get('translationType', 'unknown')

            # Define lists to store different types of sources
            valid_sources = []
            internal_sources = []
            
            # Track available priorities
            highest_priority = -1
            best_source = None

            # Process all sources and categorize them
            for source in raw_sources:
                source_url = self._decrypt_source(source.get('sourceUrl', ''))
                source_name = source.get('sourceName', '').lower()
                source_type = source.get('type', '')
                priority = float(source.get('priority', 0))

                # Deal with different source types
                if source_url.startswith("/apivtwo/"):
                    # Internal AllAnime server (handled by their player)
                    internal_sources.append({
                        'url': source_url,
                        'name': source_name,
                        'type': source_type,
                        'priority': priority
                    })

                elif source_url.startswith("http"):
                    # Direct URL we can use
                    valid_sources.append({
                        'url': source_url,
                        'name': source_name,
                        'type': source_type,
                        'priority': priority
                    })
                    
                    # Keep track of the highest priority source
                    if priority > highest_priority:
                        highest_priority = priority
                        best_source = {
                            'url': source_url,
                            'name': source_name,
                            'priority': priority
                        }

            # Process internal sources - try to extract from them if available
            for internal_source in internal_sources:
                try:
                    s_url = internal_source['url']
                    s_name = internal_source['name']
                    
                    # Get the version endpoint info
                    version_response = self.session.get(f"{self.base_url}/getVersion")
                    if version_response.status_code != 200:
                        continue
                        
                    version_data = version_response.json()
                    iframe_head = version_data.get('episodeIframeHead')
                    
                    if not iframe_head:
                        continue
                        
                    # Replace /clock? with /clock.json? as done in the reference
                    modified_url = s_url.replace("/clock?", "/clock.json?")
                    
                    # Get video link data
                    video_headers = self.headers.copy()
                    video_response = self.session.get(f"{iframe_head}{modified_url}", headers=video_headers)
                    
                    if video_response.status_code != 200:
                        continue
                        
                    # Parse the response
                    link_data = video_response.json()
                    links = link_data.get('links', [])
                    
                    # Process MP4 or HLS links
                    for link in links:
                        if link.get('mp4') is True:
                            # Direct MP4 link - use as a valid source
                            valid_sources.append({
                                'url': link.get('link', ''),
                                'name': f"Direct MP4 ({s_name})",
                                'priority': internal_source['priority'] + 0.5  # Boost priority slightly
                            })
                            
                            # Update best source if this is higher priority
                            if internal_source['priority'] + 0.5 > highest_priority:
                                highest_priority = internal_source['priority'] + 0.5
                                best_source = {
                                    'url': link.get('link', ''),
                                    'name': f"Direct MP4 ({s_name})",
                                    'priority': internal_source['priority'] + 0.5
                                }
                        
                        elif link.get('hls') is True:
                            # HLS link - also a valid source
                            valid_sources.append({
                                'url': link.get('link', ''),
                                'name': f"HLS ({s_name})",
                                'priority': internal_source['priority'] + 0.6  # Slightly prefer HLS
                            })
                            
                            # Update best source if this is higher priority
                            if internal_source['priority'] + 0.6 > highest_priority:
                                highest_priority = internal_source['priority'] + 0.6
                                best_source = {
                                    'url': link.get('link', ''),
                                    'name': f"HLS ({s_name})",
                                    'priority': internal_source['priority'] + 0.6
                                }
                                
                except Exception as e:
                    print(f"Error processing internal source: {e}")

            # If we still don't have a valid source, return an error
            if not best_source:
                print("No valid sources found after processing")
                return Episode(
                    id=episode_id,
                    title=f"Episode {episode_string}",
                    url="",
                    quality="unknown",
                    language=language
                )

            # Return the best source we found
            return Episode(
                id=episode_id,
                title=f"Episode {episode_string}",
                url=best_source['url'],
                quality=f"{self.preferences['preferred_quality']} ({best_source['name']})",
                language=language
            )

        except Exception as e:
            print(f"Error fetching episode: {e}")
            return Episode(
                id=episode_id,
                title="Error",
                url="",
                quality="unknown",
                language="unknown"
            )

    def _slugify(self, text: str) -> str:
        if not text:
            return ""
        text = text.lower()
        text = re.sub(r'[^a-z0-9]+', '-', text).strip('-')
        return re.sub(r'-{2,}', '-', text)

    def _decrypt_source(self, source_url: str) -> str:
        if not source_url or not source_url.startswith("-"):
            return source_url

        try:
            hex_part = source_url.split('-')[-1]
            decoded_bytes = bytes.fromhex(hex_part)
            decrypted_bytes = bytes([b ^ 56 for b in decoded_bytes])
            return decrypted_bytes.decode('utf-8', errors='replace')
        except Exception as e:
            print(f"Error decrypting source URL: {e}")
            return source_url

    def _parse_status(self, status_string: Optional[str]) -> str:
        status_map = {
            "Releasing": "Ongoing",
            "Finished": "Completed",
            "Not Yet Released": "Ongoing",
            "Cancelled": "Cancelled",
            "On Hiatus": "On Hiatus",
        }
        return status_map.get(status_string, "Unknown") if status_string else "Unknown"

    def _get_filters(self) -> Dict[str, Any]:
        return {
            "origin": [
                {"id": "ALL", "name": "All"},
                {"id": "JP", "name": "Japan"},
                {"id": "CN", "name": "China"},
                {"id": "KR", "name": "Korea"}
            ],
            "seasons": [
                {"id": "all", "name": "All"},
                {"id": "Winter", "name": "Winter"},
                {"id": "Spring", "name": "Spring"},
                {"id": "Summer", "name": "Summer"},
                {"id": "Fall", "name": "Fall"}
            ],
            "years": [{"id": str(year), "name": str(year)} for year in range(2024, 1974, -1)],
            "sortBy": [
                {"id": "update", "name": "Update"},
                {"id": "Name_ASC", "name": "Name Asc"},
                {"id": "Name_DESC", "name": "Name Desc"},
                {"id": "Top", "name": "Ratings"}
            ],
            "types": [
                {"id": "Movie", "name": "Movie"},
                {"id": "ONA", "name": "ONA"},
                {"id": "OVA", "name": "OVA"},
                {"id": "Special", "name": "Special"},
                {"id": "TV", "name": "TV"}
            ],
            "genres": [
                {"id": "Action", "name": "Action"},
                {"id": "Adventure", "name": "Adventure"},
                {"id": "Comedy", "name": "Comedy"},
                {"id": "Drama", "name": "Drama"},
                {"id": "Fantasy", "name": "Fantasy"},
                {"id": "Horror", "name": "Horror"},
                {"id": "Mystery", "name": "Mystery"},
                {"id": "Romance", "name": "Romance"},
                {"id": "Sci-Fi", "name": "Sci-Fi"},
                {"id": "Slice of Life", "name": "Slice of Life"},
                {"id": "Supernatural", "name": "Supernatural"},
                {"id": "Thriller", "name": "Thriller"}
            ],
            "quality": self.available_qualities
        }