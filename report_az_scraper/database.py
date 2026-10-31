"""
database.py - SQLite database management for report.az scraper
"""
import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any
from contextlib import contextmanager

from models import Article, Category, MediaItem, ArticleTag, ScrapingLog, FailedUrl, DiscoveredUrl

logger = logging.getLogger(__name__)

DB_PATH = Path("output/report_az.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
    return conn


@contextmanager
def db_transaction():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def init_database():
    """Initialize all database tables"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    with db_transaction() as conn:
        cursor = conn.cursor()
        
        # Categories table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                slug TEXT,
                url TEXT UNIQUE NOT NULL,
                parent_id INTEGER,
                parent_name TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (parent_id) REFERENCES categories(id)
            )
        """)
        
        # Articles table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                url_hash TEXT UNIQUE,
                canonical_url TEXT,
                title TEXT,
                subtitle TEXT,
                content TEXT,
                summary TEXT,
                author TEXT,
                journalist TEXT,
                source TEXT,
                category TEXT,
                category_url TEXT,
                subcategory TEXT,
                subcategory_url TEXT,
                language TEXT DEFAULT 'az',
                published_at TEXT,
                published_at_raw TEXT,
                updated_at TEXT,
                updated_at_raw TEXT,
                scraped_at TEXT,
                main_image_url TEXT,
                meta_description TEXT,
                meta_keywords TEXT,
                og_title TEXT,
                og_description TEXT,
                og_image TEXT,
                json_ld TEXT,
                tags TEXT,
                images TEXT,
                videos TEXT,
                related_articles TEXT,
                status TEXT DEFAULT 'pending',
                error_message TEXT,
                content_length INTEGER DEFAULT 0,
                is_incomplete INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                updated_db_at TEXT DEFAULT (datetime('now'))
            )
        """)
        
        # Article tags table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS article_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id INTEGER NOT NULL,
                tag TEXT NOT NULL,
                tag_slug TEXT,
                FOREIGN KEY (article_id) REFERENCES articles(id),
                UNIQUE(article_id, tag)
            )
        """)
        
        # Article media table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS article_media (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id INTEGER NOT NULL,
                media_type TEXT NOT NULL,
                url TEXT NOT NULL,
                alt_text TEXT,
                caption TEXT,
                title TEXT,
                width INTEGER,
                height INTEGER,
                is_main INTEGER DEFAULT 0,
                position INTEGER DEFAULT 0,
                FOREIGN KEY (article_id) REFERENCES articles(id)
            )
        """)
        
        # Discovered URLs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS discovered_urls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                source TEXT,
                discovered_at TEXT,
                status TEXT DEFAULT 'pending',
                priority INTEGER DEFAULT 0
            )
        """)
        
        # Scraping logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scraping_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                event_type TEXT,
                message TEXT,
                urls_discovered INTEGER DEFAULT 0,
                urls_scraped INTEGER DEFAULT 0,
                urls_failed INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        
        # Failed URLs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS failed_urls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                source TEXT,
                error_code INTEGER,
                error_message TEXT,
                attempts INTEGER DEFAULT 1,
                last_attempt TEXT,
                first_attempt TEXT
            )
        """)
        
        # Create indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_url ON articles(url)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_published_at ON articles(published_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_category ON articles(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_status ON articles(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_discovered_urls_status ON discovered_urls(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_discovered_urls_priority ON discovered_urls(priority DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_article_tags_article ON article_tags(article_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_article_media_article ON article_media(article_id)")
        
    logger.info(f"Database initialized at {DB_PATH}")


def save_category(category: Category) -> Optional[int]:
    """Save or update a category. Returns the category ID."""
    try:
        with db_transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO categories (name, slug, url, parent_id, parent_name)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                    name = excluded.name,
                    slug = excluded.slug,
                    parent_id = excluded.parent_id,
                    parent_name = excluded.parent_name
            """, (category.name, category.slug, category.url, 
                  category.parent_id, category.parent_name))
            return cursor.lastrowid
    except Exception as e:
        logger.error(f"Error saving category {category.url}: {e}")
        return None


def save_article(article: Article) -> Optional[int]:
    """Save or update an article. Returns the article ID."""
    try:
        with db_transaction() as conn:
            cursor = conn.cursor()
            
            # Check if article exists
            cursor.execute("SELECT id, status FROM articles WHERE url = ?", (article.url,))
            existing = cursor.fetchone()
            
            if existing:
                article_id = existing['id']
                # Only update if new data is better
                if article.status == 'success' or existing['status'] != 'success':
                    cursor.execute("""
                        UPDATE articles SET
                            canonical_url = ?, title = ?, subtitle = ?, content = ?,
                            summary = ?, author = ?, journalist = ?, source = ?,
                            category = ?, category_url = ?, subcategory = ?, subcategory_url = ?,
                            language = ?, published_at = ?, published_at_raw = ?,
                            updated_at = ?, updated_at_raw = ?, scraped_at = ?,
                            main_image_url = ?, meta_description = ?, meta_keywords = ?,
                            og_title = ?, og_description = ?, og_image = ?,
                            json_ld = ?, tags = ?, images = ?, videos = ?,
                            related_articles = ?, status = ?, error_message = ?,
                            content_length = ?, is_incomplete = ?,
                            url_hash = ?, updated_db_at = datetime('now')
                        WHERE id = ?
                    """, (
                        article.canonical_url, article.title, article.subtitle, article.content,
                        article.summary, article.author, article.journalist, article.source,
                        article.category, article.category_url, article.subcategory, article.subcategory_url,
                        article.language,
                        article.published_at.isoformat() if article.published_at else None,
                        article.published_at_raw,
                        article.updated_at.isoformat() if article.updated_at else None,
                        article.updated_at_raw,
                        article.scraped_at.isoformat() if article.scraped_at else None,
                        article.main_image_url, article.meta_description, article.meta_keywords,
                        article.og_title, article.og_description, article.og_image,
                        article.json_ld,
                        json.dumps(article.tags, ensure_ascii=False),
                        json.dumps(article.images, ensure_ascii=False),
                        json.dumps(article.videos, ensure_ascii=False),
                        json.dumps(article.related_articles, ensure_ascii=False),
                        article.status, article.error_message,
                        article.content_length, int(article.is_incomplete),
                        article.get_url_hash(),
                        article_id
                    ))
            else:
                cursor.execute("""
                    INSERT INTO articles (
                        url, url_hash, canonical_url, title, subtitle, content,
                        summary, author, journalist, source,
                        category, category_url, subcategory, subcategory_url,
                        language, published_at, published_at_raw,
                        updated_at, updated_at_raw, scraped_at,
                        main_image_url, meta_description, meta_keywords,
                        og_title, og_description, og_image, json_ld,
                        tags, images, videos, related_articles,
                        status, error_message, content_length, is_incomplete
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    article.url, article.get_url_hash(), article.canonical_url,
                    article.title, article.subtitle, article.content,
                    article.summary, article.author, article.journalist, article.source,
                    article.category, article.category_url, article.subcategory, article.subcategory_url,
                    article.language,
                    article.published_at.isoformat() if article.published_at else None,
                    article.published_at_raw,
                    article.updated_at.isoformat() if article.updated_at else None,
                    article.updated_at_raw,
                    article.scraped_at.isoformat() if article.scraped_at else None,
                    article.main_image_url, article.meta_description, article.meta_keywords,
                    article.og_title, article.og_description, article.og_image,
                    article.json_ld,
                    json.dumps(article.tags, ensure_ascii=False),
                    json.dumps(article.images, ensure_ascii=False),
                    json.dumps(article.videos, ensure_ascii=False),
                    json.dumps(article.related_articles, ensure_ascii=False),
                    article.status, article.error_message,
                    article.content_length, int(article.is_incomplete)
                ))
                article_id = cursor.lastrowid
            
            return article_id
    except Exception as e:
        logger.error(f"Error saving article {article.url}: {e}")
        return None


def save_article_tags(article_id: int, tags: List[str]):
    """Save article tags"""
    if not tags:
        return
    try:
        with db_transaction() as conn:
            cursor = conn.cursor()
            for tag in tags:
                tag_slug = tag.lower().replace(' ', '-')
                cursor.execute("""
                    INSERT OR IGNORE INTO article_tags (article_id, tag, tag_slug)
                    VALUES (?, ?, ?)
                """, (article_id, tag, tag_slug))
    except Exception as e:
        logger.error(f"Error saving tags for article {article_id}: {e}")


def save_article_media(article_id: int, media_items: List[MediaItem]):
    """Save article media"""
    if not media_items:
        return
    try:
        with db_transaction() as conn:
            cursor = conn.cursor()
            # Remove old media for this article
            cursor.execute("DELETE FROM article_media WHERE article_id = ?", (article_id,))
            for item in media_items:
                cursor.execute("""
                    INSERT INTO article_media (
                        article_id, media_type, url, alt_text, caption, title,
                        width, height, is_main, position
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    article_id, item.media_type, item.url, item.alt_text,
                    item.caption, item.title, item.width, item.height,
                    int(item.is_main), item.position
                ))
    except Exception as e:
        logger.error(f"Error saving media for article {article_id}: {e}")


def add_discovered_urls(urls: List[DiscoveredUrl]) -> int:
    """Add discovered URLs to the queue. Returns count of new URLs added."""
    if not urls:
        return 0
    added = 0
    try:
        with db_transaction() as conn:
            cursor = conn.cursor()
            for du in urls:
                cursor.execute("""
                    INSERT OR IGNORE INTO discovered_urls (url, source, discovered_at, status, priority)
                    VALUES (?, ?, ?, ?, ?)
                """, (du.url, du.source, du.discovered_at.isoformat(), du.status, du.priority))
                if cursor.rowcount > 0:
                    added += 1
        return added
    except Exception as e:
        logger.error(f"Error adding discovered URLs: {e}")
        return 0


def get_pending_urls(limit: int = 100) -> List[Dict]:
    """Get pending URLs for scraping, ordered by priority"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT url, source, priority FROM discovered_urls
            WHERE status = 'pending'
            ORDER BY priority DESC, id ASC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def update_url_status(url: str, status: str):
    """Update the status of a discovered URL"""
    try:
        with db_transaction() as conn:
            conn.execute(
                "UPDATE discovered_urls SET status = ? WHERE url = ?",
                (status, url)
            )
    except Exception as e:
        logger.error(f"Error updating URL status for {url}: {e}")


def save_failed_url(failed: FailedUrl):
    """Save or update a failed URL"""
    try:
        with db_transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO failed_urls (url, source, error_code, error_message, attempts, last_attempt, first_attempt)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                    error_code = excluded.error_code,
                    error_message = excluded.error_message,
                    attempts = failed_urls.attempts + 1,
                    last_attempt = excluded.last_attempt
            """, (
                failed.url, failed.source, failed.error_code, failed.error_message,
                failed.attempts,
                failed.last_attempt.isoformat() if failed.last_attempt else None,
                failed.first_attempt.isoformat() if failed.first_attempt else None
            ))
    except Exception as e:
        logger.error(f"Error saving failed URL {failed.url}: {e}")


def save_scraping_log(log: ScrapingLog):
    """Save a scraping log entry"""
    try:
        with db_transaction() as conn:
            conn.execute("""
                INSERT INTO scraping_logs (session_id, event_type, message, 
                    urls_discovered, urls_scraped, urls_failed, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                log.session_id, log.event_type, log.message,
                log.urls_discovered, log.urls_scraped, log.urls_failed,
                log.created_at.isoformat() if log.created_at else datetime.now().isoformat()
            ))
    except Exception as e:
        logger.error(f"Error saving scraping log: {e}")


def is_url_scraped(url: str) -> bool:
    """Check if a URL has already been scraped successfully"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM articles WHERE url = ? AND status = 'success'", (url,)
        )
        return cursor.fetchone() is not None
    finally:
        conn.close()


def is_url_discovered(url: str) -> bool:
    """Check if a URL is already in discovered_urls"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM discovered_urls WHERE url = ?", (url,))
        return cursor.fetchone() is not None
    finally:
        conn.close()


def get_stats() -> Dict:
    """Get comprehensive scraping statistics"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        stats = {}
        
        cursor.execute("SELECT COUNT(*) FROM discovered_urls")
        stats['total_discovered'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM articles WHERE status = 'success'")
        stats['total_scraped'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM failed_urls")
        stats['total_failed'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM categories")
        stats['total_categories'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM article_media WHERE media_type = 'image'")
        stats['total_images'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM article_media WHERE media_type = 'video'")
        stats['total_videos'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT MIN(published_at) FROM articles WHERE published_at IS NOT NULL AND status='success'")
        row = cursor.fetchone()
        stats['oldest_article'] = row[0] if row else None
        
        cursor.execute("SELECT MAX(published_at) FROM articles WHERE published_at IS NOT NULL AND status='success'")
        row = cursor.fetchone()
        stats['newest_article'] = row[0] if row else None
        
        cursor.execute("SELECT COUNT(*) FROM articles WHERE published_at IS NULL AND status='success'")
        stats['no_date_count'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM articles WHERE is_incomplete = 1 AND status='success'")
        stats['incomplete_count'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM discovered_urls WHERE status = 'pending'")
        stats['pending_count'] = cursor.fetchone()[0]
        
        return stats
    finally:
        conn.close()


def get_all_articles_ordered(order: str = 'asc') -> List[Dict]:
    """Get all successfully scraped articles ordered by published_at"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        direction = "ASC" if order == 'asc' else "DESC"
        cursor.execute(f"""
            SELECT * FROM articles 
            WHERE status = 'success'
            ORDER BY 
                CASE WHEN published_at IS NULL THEN 1 ELSE 0 END,
                published_at {direction},
                id {direction}
        """)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_db_size() -> int:
    """Get database file size in bytes"""
    try:
        return DB_PATH.stat().st_size
    except:
        return 0

