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

                    # Create episode IDs dictionary in format "anime_id-episode_number"
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
            print(f"Getting episode: {episode_id[:100]}...")
            
            # Parse the episode ID (format: anime_id-episode_number)
            if "-" not in episode_id:
                print(f"Invalid episode_id format: {episode_id}")
                return Episode(
                    id=episode_id,
                    title="Invalid ID Format",
                    url="",
                    quality="unknown",
                    language="unknown"
                )
                
            anime_id, episode_number = episode_id.split("-", 1)
            
            # Prepare the data for the API request
            data = {
                "variables": {
                    "showId": anime_id,
                    "translationType": self.preferences["preferred_sub"],
                    "episodeString": episode_number
                },
                "query": self.streams_query
            }
            
            # Make the API request to get sources
            response = self.session.post(
                f"{self.api_url}/api",
                json=data,
                headers=self.headers
            )

            if response.status_code != 200:
                print(f"Error: API returned status code {response.status_code}")
                return Episode(
                    id=episode_id,
                    title="API Error",
                    url="",
                    quality="unknown",
                    language="unknown"
                )

            # Parse the API response
            try:
                response_data = response.json()
            except json.JSONDecodeError as je:
                print(f"Error parsing API response JSON: {je}")
                print(f"Raw response: {response.text[:200]}")
                return Episode(
                    id=episode_id,
                    title="API Response Error",
                    url="",
                    quality="unknown",
                    language="unknown"
                )

            # Extract episode data
            episode_data = response_data.get('data', {}).get('episode', {})
            if not episode_data or 'sourceUrls' not in episode_data:
                print(f"No streams found in API response")
                return Episode(
                    id=episode_id,
                    title="No streams found",
                    url="",
                    quality="unknown",
                    language="unknown"
                )

            # Get all source URLs
            raw_sources = episode_data.get('sourceUrls', [])
            if not raw_sources:
                print(f"Source URLs list is empty")
                return Episode(
                    id=episode_id,
                    title="No sources found",
                    url="",
                    quality="unknown",
                    language="unknown"
                )

            # ONLY LOOK FOR OKRU SOURCES
            okru_source = None
            highest_priority = -1

            print(f"Found {len(raw_sources)} potential sources, looking for OKRU only")
            for source in raw_sources:
                source_url = self._decrypt_source(source.get('sourceUrl', ''))
                source_name = source.get('sourceName', '').lower()
                priority = float(source.get('priority', 0))

                if not source_url:
                    continue

                # Check if it's an OKRU source
                if "ok.ru" in source_url or "okru" in source_name:
                    print(f"Found OKRU source: {source_url}")
                    if priority > highest_priority:
                        highest_priority = priority
                        okru_source = {
                            'url': source_url,
                            'name': source_name,
                            'priority': priority
                        }

            # If no OKRU source found, return error
            if not okru_source:
                print("No OKRU sources found")
                return Episode(
                    id=episode_id,
                    title="No OKRU source",
                    url="",
                    quality="unknown",
                    language="unknown"
                )

            # Extract video URL from OKRU
            print(f"Extracting URL from OKRU source: {okru_source['url']}")
            try:
                # Get the OKRU page
                okru_response = self.session.get(okru_source['url'], headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
                    'Accept': '*/*',
                    'Referer': self.base_url
                })
                
                if okru_response.status_code != 200:
                    print(f"Failed to get OKRU page: {okru_response.status_code}")
                    # Return the source URL if we can't extract the direct streaming URL
                    return Episode(
                        id=episode_id,
                        title="OKRU Source",
                        url=okru_source['url'],
                        quality=self.preferences["preferred_quality"],
                        language="unknown"
                    )
                
                # Find the data-options attribute in div element
                data_options_match = re.search(r'data-options="([^"]+)"', okru_response.text)
                if not data_options_match:
                    print("No data-options found in OKRU page")
                    # Return the source URL if we can't extract the direct streaming URL
                    return Episode(
                        id=episode_id,
                        title="OKRU Source",
                        url=okru_source['url'],
                        quality=self.preferences["preferred_quality"],
                        language="unknown"
                    )
                
                # Extract and clean up the data-options attribute
                data_options = data_options_match.group(1)
                data_options = data_options.replace('&quot;', '"')
                
                # Extract the metadata which contains the video URLs
                metadata_match = re.search(r'"metadata":"(.*?[^\\])"', data_options)
                if not metadata_match:
                    print("No metadata found in data-options")
                    return Episode(
                        id=episode_id,
                        title="OKRU Source",
                        url=okru_source['url'],
                        quality=self.preferences["preferred_quality"],
                        language="unknown"
                    )
                
                # Parse the metadata JSON
                metadata_json = metadata_match.group(1).replace('\\"', '"')
                try:
                    metadata = json.loads(metadata_json)
                except json.JSONDecodeError as je:
                    print(f"Error parsing metadata JSON: {je}")
                    print(f"Metadata JSON: {metadata_json[:100]}...")
                    return Episode(
                        id=episode_id,
                        title="OKRU Source",
                        url=okru_source['url'],
                        quality=self.preferences["preferred_quality"],
                        language="unknown"
                    )
                
                # Get the video URLs
                videos = metadata.get('videos', [])
                if not videos:
                    print("No videos found in metadata")
                    return Episode(
                        id=episode_id,
                        title="OKRU Source",
                        url=okru_source['url'],
                        quality=self.preferences["preferred_quality"],
                        language="unknown"
                    )
                
                # Sort videos by quality (highest first)
                # OKRU typically has mp4 videos with names like "mobile", "lowest", "low", "sd", "hd"
                # The first one is usually the highest quality
                best_video = videos[0]
                streaming_url = best_video.get('url', '')
                quality = best_video.get('name', 'unknown')
                
                print(f"Found OKRU streaming URL: {streaming_url[:50]}...")
                
                # Extract episode info from the data
                variables = data.get('variables', {})
                episode_string = variables.get('episodeString', 'unknown')
                language = variables.get('translationType', 'unknown')
                
                return Episode(
                    id=episode_id,
                    title=f"Episode {episode_string}",
                    url=streaming_url if streaming_url else okru_source['url'],
                    quality=f"OKRU {quality}",
                    language=language
                )
                
            except Exception as e:
                import traceback
                print(f"Error extracting from OKRU: {e}")
                print(traceback.format_exc())
                
                # Fall back to returning the OKRU source URL if extraction failed
                return Episode(
                    id=episode_id,
                    title="OKRU Source",
                    url=okru_source['url'],
                    quality=self.preferences["preferred_quality"],
                    language="unknown"
                )

        except Exception as e:
            import traceback
            print(f"Error fetching episode: {e}")
            print(traceback.format_exc())
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