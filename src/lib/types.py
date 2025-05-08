import requests
import os

class Manga():
    def __init__(self, id: str, url: str, title: str, author: str, description: str, poster: str, chapters: int, tags:list=[], genres: list=[], status: str="Ongoing", rating: float=-1.00, chapter_ids: dict= {"Chapter 1": "xxxxxxxx"}):
        self.id = id
        self.url = url
        #self.name = name
        self.title = title
        self.author = author
        self.description = description
        self.poster = poster
        self.chapters = chapters
        #self.chapter_and_pages = chapter_and_pages
        self.tags = tags
        self.genres = genres
        self.status = status
        self.rating = rating
        self.chapter_ids = chapter_ids
    
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
            "url": self.url,
            "chapter_ids": self.chapter_ids
            
            #"chapters_and_pages": self._chapters_and_pages_model
        }

class Chapter():
    def __init__(self, title: str, pages: list, id):
        self.id = id
        self.title = title
        self.pages = pages   
        self.total_pages = len(pages)

    def get(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "total_pages": self.total_pages,
            "pages": self.pages
        }

class Scraper():
    def __init__(self, name="Missing Name", url="Missing Url", api_url=None, scraper_version="1.0.0"):
        self.name = name
        self.base_url = url
        self.api_url = api_url
        self.scraper_version = scraper_version
        self.available_filters = {}
        self.available_qualities = []