import requests
import os

class Manga():
    def __init__(self, id: str, url: str, title: str, author: str, description: str, poster: str, chapters: int, chapter_and_pages: dict, tags: list=None, genres: list=None, status: str="Ongoing", rating: float=-1.00):
        self.id = id
        self.url = url
        self.title = title
        self.author = author
        self.description = description
        self.poster = poster
        self.chapters = chapters
        self.chapter_and_pages = chapter_and_pages
        self.tags = tags
        self.genres = genres
        self.status = status
        self.rating = rating

    def _chapters_and_pages_model(self):
        """General Structure of the chapters and pages"""
        return {
            "chapters": [
                {
                    "title": "Chapter 1 - Name Of The Chapter",
                    "total_pages": 3,
                    "pages": ["page_url_1", "page_url_2"] # And so on.
                },
                {
                    "title": "Chapter 2 - Name Of The Chapter",
                    "total_pages": 3,
                    "pages": ["page_url_1", "page_url_2"]
                },
            ],
        }

    def get(self) -> dict:
        return {
            "title": self.title,
            "author": self.author,
            "description": self.description,
            "poster": self.poster,
            "total_chapters": self.chapters,
            "tags": self.tags,
            "genres": self.genres,
            "status": self.status,
            "rating": self.rating,
            "chapters_and_pages": self._chapters_and_pages_model
        }


class Anime():
    def __init__(self, title: str, description: str, poster: str, episodes: int, episode_and_videos: dict, tags: list=None, genres: list=None, status: str="Ongoing", rating: float=-1.00):
        self.title = title
        self.description = description
        self.poster = poster
        self.episodes = episodes
        self.episode_and_videos = episode_and_videos
        self.tags = tags
        self.genres = genres
        self.status = status
        self.rating = rating

    def _episodes_and_videos_model(self):
        """General Structure of the episodes and videos"""
        return {
            "episodes":
                {
                    "title": "Episode 1 - Name Of The Episode",
                    "total_episodes": 3,
                    "streaming_links": {
                        "1080p": "video_url_1",
                        "720p": "video_url_2",
                        "480p": "video_url_3",
                        "360p": "video_url_4",
                        "240p": "video_url_5",
                        "144p": "video_url_6",
                        "required": "Must have one quality or more"
                    }
                },
            }


    def get(self) -> dict:
        return {
            "title": self.title,
            "description": self.description,
            "poster": self.poster,
            "total_episodes": self.episodes,
            "tags": self.tags,
            "genres": self.genres,
            "status": self.status,
            "rating": self.rating,
            "episodes_and_videos": self._episodes_and_videos_model
        }

class Scraper():
    def __init__(self, name="Missing Name", url="Missing Url", api_url=None, scraper_version="1.0.0"):
        self.base_url = url
        self.api_url = api_url
        self.scraper_version = scraper_version
        self.available_filters = {}
        self.available_qualities = []