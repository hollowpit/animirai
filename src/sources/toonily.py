
import json
import re
import time
import requests
import cloudscraper
from typing import List, Dict, Any, Optional
from datetime import datetime
from src.lib.types import Scraper, Manga, Chapter

class Toonily(Scraper):
    def __init__(self):
        super().__init__(
            name="Toonily",
            url="https://toonily.com",
            scraper_version="1.0.0"
        )
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
            "Accept": "text/html,application/xhtml+xml,application/xml",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": self.base_url,
            "Connection": "keep-alive",
        }
        
        # Set mature content cookie
        self.session.cookies.set("toonily-mature", "1", domain="toonily.com")
        self.manga_subpath = "serie"

    def popular_manga(self, page: int = 1) -> List[Manga]:
        url = f"{self.base_url}/{self.manga_subpath}/page/{page}?m_orderby=views"
        
        print(f"Requesting popular manga from: {url}")
        response = self.session.get(url, headers=self.headers)
        if response.status_code != 200:
            print(f"Error: Status code {response.status_code}")
            return []
            
        html = response.text
        print(f"Response received, length: {len(html)}")
        manga_items = self._extract_manga_items(html)
        print(f"Extracted {len(manga_items)} manga items")
        return [self._create_manga_from_element(item) for item in manga_items]

    def latest_manga(self, page: int = 1) -> List[Manga]:
        url = f"{self.base_url}/{self.manga_subpath}/page/{page}?m_orderby=latest"
        
        response = self.session.get(url, headers=self.headers)
        if response.status_code != 200:
            return []
            
        html = response.text
        manga_items = self._extract_manga_items(html)
        return [self._create_manga_from_element(item) for item in manga_items]

    def search_manga(self, query: str, page: int = 1) -> List[Manga]:
        query = re.sub(r'[^a-zA-Z0-9]+', ' ', query).strip()
        url = f"{self.base_url}/?s={query}&post_type=wp-manga"
        
        response = self.session.get(url, headers=self.headers)
        if response.status_code != 200:
            return []
            
        html = response.text
        manga_items = self._extract_search_items(html)
        return [self._create_manga_from_element(item) for item in manga_items]

    def _extract_manga_items(self, html: str) -> List[Dict[str, str]]:
        pattern = r'<div\s+class="page-item-detail\s+manga">\s*<div\s+class="item-thumb\s+c-image-hover">\s*<a\s+href="([^"]+)"[^>]*>\s*<img\s+(?:class="[^"]*"\s+)?(?:data-src|src)="([^"]+)"[^>]*>.*?<h3\s+class="h5">\s*<a[^>]*>(.*?)</a>'
        matches = re.findall(pattern, html, re.DOTALL)
        
        manga_items = []
        for url, img_url, title in matches:
            img_url = self._process_cover_url(img_url)
            title = re.sub(r'<[^>]+>', '', title).strip()
            manga_items.append({
                "url": url,
                "title": title,
                "img_url": img_url
            })
                
        return manga_items

    def _extract_search_items(self, html: str) -> List[Dict[str, str]]:
        pattern = r'<div\s+class="row\s+c-tabs-item__content">\s*<div\s+class="col-4[^"]*">\s*<a\s+href="([^"]+)"[^>]*>\s*<img\s+(?:class="[^"]*"\s+)?(?:data-src|src)="([^"]+)"[^>]*>.*?<div\s+class="post-title">\s*<a[^>]*>(.*?)</a>'
        
        matches = re.findall(pattern, html, re.DOTALL)
        
        manga_items = []
        for url, img_url, title in matches:
            img_url = self._process_cover_url(img_url)
            title = re.sub(r'<[^>]+>', '', title).strip()
            manga_items.append({
                "url": url,
                "title": title,
                "img_url": img_url
            })
                
        return manga_items

    def _create_manga_from_element(self, item: Dict[str, str]) -> Manga:
        manga_id = self._extract_manga_id(item["url"])
        return Manga(
            id=manga_id,
            url=item["url"],
            title=item["title"],
            author="",
            description="",
            poster=item["img_url"],
            chapters=0,
            chapter_ids={}
        )

    def _process_cover_url(self, url: str) -> str:
        sd_cover_regex = r'-\d+x\d+(\.\w+)$'
        if re.search(sd_cover_regex, url):
            return re.sub(sd_cover_regex, r'\1', url)
        return url

    def _extract_manga_id(self, url: str) -> str:
        pattern = rf'{self.manga_subpath}/([^/]+)'
        match = re.search(pattern, url)
        if match:
            return match.group(1)
        return url.split('/')[-2]

    def manga_details(self, manga_id: str) -> Manga:
        url = f"{self.base_url}/{self.manga_subpath}/{manga_id}"
        
        response = self.session.get(url, headers=self.headers)
        if response.status_code != 200:
            return None
            
        html = response.text
        
        title_pattern = r'<div class="post-title">.*?<h1>(.*?)</h1>'
        author_pattern = r'<div class="author-content">.*?<a[^>]*>(.*?)</a>'
        desc_pattern = r'<div class="description-summary">.*?<div class="summary__content[^"]*">(.*?)</div>'
        img_pattern = r'<div class="summary_image">.*?<img[^>]*data-src="([^"]*)"[^>]*>'
        status_pattern = r'<div class="post-status">.*?<div class="summary-content">(.*?)</div>'
        rating_pattern = r'<div class="post-rating">.*?<span class="score">(.*?)</span>'
        genres_pattern = r'<div class="genres-content">.*?<a[^>]*>(.*?)</a>'
        chapter_list_pattern = r'<li\s+class="wp-manga-chapter[^"]*">\s*<a\s+href="([^"]+)"[^>]*>(.*?)</a>'
        
        title_match = re.search(title_pattern, html, re.DOTALL)
        author_match = re.search(author_pattern, html, re.DOTALL)
        desc_match = re.search(desc_pattern, html, re.DOTALL)
        img_match = re.search(img_pattern, html, re.DOTALL)
        status_match = re.search(status_pattern, html, re.DOTALL)
        rating_match = re.search(rating_pattern, html, re.DOTALL)
        
        genres = re.findall(genres_pattern, html, re.DOTALL)
        chapters = re.findall(chapter_list_pattern, html, re.DOTALL)
        
        title = title_match.group(1) if title_match else ""
        author = author_match.group(1) if author_match else ""
        description = desc_match.group(1).strip() if desc_match else ""
        description = re.sub(r'<[^>]*>', '', description)
        
        img_url = ""
        if img_match:
            img_url = self._process_cover_url(img_match.group(1))
            
        status = status_match.group(1).strip() if status_match else "Ongoing"
        rating = float(rating_match.group(1)) if rating_match else -1.0
        
        chapter_ids = {}
        for chapter_url, chapter_title in chapters:
            # Extract chapter ID from URL
            chapter_parts = chapter_url.rstrip('/').split('/')
            if len(chapter_parts) >= 2:
                chapter_id = chapter_parts[-2]
                clean_title = re.sub(r'<[^>]+>', '', chapter_title).strip()
                chapter_ids[clean_title] = chapter_id
        
        return Manga(
            id=manga_id,
            url=url,
            title=title,
            author=author,
            description=description,
            poster=img_url,
            chapters=len(chapter_ids),
            tags=genres,
            genres=genres,
            status=status,
            rating=rating,
            chapter_ids=chapter_ids
        )
        
    def get_chapter(self, chapter_id: str) -> Chapter:
        url = f"{self.base_url}/{chapter_id}"
        
        response = self.session.get(url, headers=self.headers)
        if response.status_code != 200:
            return None
            
        html = response.text
        
        title_pattern = r'<ol class="breadcrumb">.*?<li class="active">(.*?)</li>'
        img_pattern = r'<div class="page-break\s*(?:no-gaps)?">\s*<img[^>]*data-src="([^"]*)"[^>]*>'
        
        title_match = re.search(title_pattern, html, re.DOTALL)
        images = re.findall(img_pattern, html, re.DOTALL)
        
        title = title_match.group(1).strip() if title_match else f"Chapter {chapter_id}"
        
        return Chapter(
            id=chapter_id,
            title=title,
            pages=images
        )
