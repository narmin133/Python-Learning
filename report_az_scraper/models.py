"""
models.py - Pydantic data models for report.az scraper
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, HttpUrl, field_validator
import hashlib


class Category(BaseModel):
    id: Optional[int] = None
    name: str
    slug: str
    url: str
    parent_id: Optional[int] = None
    parent_name: Optional[str] = None

    class Config:
        populate_by_name = True


class MediaItem(BaseModel):
    article_id: Optional[int] = None
    media_type: str  # 'image' or 'video'
    url: str
    alt_text: Optional[str] = None
    caption: Optional[str] = None
    title: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    is_main: bool = False
    position: int = 0


class ArticleTag(BaseModel):
    article_id: Optional[int] = None
    tag: str
    tag_slug: Optional[str] = None


class Article(BaseModel):
    id: Optional[int] = None
    url: str
    canonical_url: Optional[str] = None
    title: Optional[str] = None
    subtitle: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None
    author: Optional[str] = None
    journalist: Optional[str] = None
    source: Optional[str] = None
    category: Optional[str] = None
    category_url: Optional[str] = None
    subcategory: Optional[str] = None
    subcategory_url: Optional[str] = None
    language: Optional[str] = None
    published_at: Optional[datetime] = None
    published_at_raw: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_at_raw: Optional[str] = None
    scraped_at: Optional[datetime] = None
    main_image_url: Optional[str] = None
    meta_description: Optional[str] = None
    meta_keywords: Optional[str] = None
    og_title: Optional[str] = None
    og_description: Optional[str] = None
    og_image: Optional[str] = None
    json_ld: Optional[str] = None
    tags: List[str] = []
    images: List[str] = []
    videos: List[str] = []
    related_articles: List[str] = []
    status: str = 'pending'  # pending, success, failed
    error_message: Optional[str] = None
    content_length: int = 0
    is_incomplete: bool = False

    def get_url_hash(self) -> str:
        return hashlib.md5(self.url.encode()).hexdigest()

    class Config:
        populate_by_name = True


class DiscoveredUrl(BaseModel):
    url: str
    source: str  # sitemap, category, pagination, internal_link, rss
    discovered_at: datetime
    status: str = 'pending'  # pending, scraped, failed, skipped
    priority: int = 0  # higher = more important


class ScrapingLog(BaseModel):
    id: Optional[int] = None
    session_id: str
    event_type: str  # started, completed, error, checkpoint
    message: str
    urls_discovered: int = 0
    urls_scraped: int = 0
    urls_failed: int = 0
    created_at: datetime = None

    def __init__(self, **data):
        if data.get('created_at') is None:
            data['created_at'] = datetime.now()
        super().__init__(**data)


class FailedUrl(BaseModel):
    url: str
    source: str
    error_code: Optional[int] = None
    error_message: Optional[str] = None
    attempts: int = 1
    last_attempt: datetime = None
    first_attempt: datetime = None

    def __init__(self, **data):
        now = datetime.now()
        if data.get('last_attempt') is None:
            data['last_attempt'] = now
        if data.get('first_attempt') is None:
            data['first_attempt'] = now
        super().__init__(**data)


class ScrapingStats(BaseModel):
    total_discovered: int = 0
    total_scraped: int = 0
    total_failed: int = 0
    total_duplicates: int = 0
    total_categories: int = 0
    total_images: int = 0
    total_videos: int = 0
    oldest_article_date: Optional[datetime] = None
    newest_article_date: Optional[datetime] = None
    no_date_count: int = 0
    incomplete_content_count: int = 0
    scraping_duration_seconds: float = 0
    db_size_bytes: int = 0

