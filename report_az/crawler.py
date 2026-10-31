"""
crawler.py - Main crawler that fetches and parses article pages
"""
import time
import logging
import uuid
from datetime import datetime
from typing import List, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from models import Article, MediaItem, FailedUrl, ScrapingLog, DiscoveredUrl
from database import (
    save_article, save_article_tags, save_article_media, save_failed_url,
    save_scraping_log, update_url_status, get_pending_urls, is_url_scraped,
    add_discovered_urls, get_stats
)
from article_parser import parse_article, extract_images, extract_videos
from discovery import normalize_url, is_article_url, HEADERS

logger = logging.getLogger(__name__)

BASE_URL = "https://report.az"
SESSION_ID = str(uuid.uuid4())[:8]


class RateLimiter:
    """Simple rate limiter with minimum delay between requests"""
    
    def __init__(self, min_delay: float = 0.5, max_delay: float = 2.0):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.last_request = 0
    
    def wait(self):
        import random
        elapsed = time.time() - self.last_request
        delay = random.uniform(self.min_delay, self.max_delay)
        if elapsed < delay:
            time.sleep(delay - elapsed)
        self.last_request = time.time()


def create_session() -> requests.Session:
    """Create a requests session with appropriate settings"""
    session = requests.Session()
    session.headers.update(HEADERS)
    
    adapter = requests.adapters.HTTPAdapter(
        max_retries=requests.adapters.Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
    )
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    
    return session


def fetch_article(url: str, session: requests.Session, timeout: int = 30) -> tuple:
    """
    Fetch an article page. Returns (status_code, html_content, final_url)
    """
    try:
        resp = session.get(url, timeout=timeout, allow_redirects=True)
        resp.encoding = 'utf-8'
        return resp.status_code, resp.text, str(resp.url)
    except requests.exceptions.Timeout:
        logger.warning(f"Timeout fetching {url}")
        return 0, "", url
    except requests.exceptions.ConnectionError as e:
        logger.warning(f"Connection error for {url}: {e}")
        return 0, "", url
    except Exception as e:
        logger.error(f"Error fetching {url}: {e}")
        return 0, "", url


def scrape_article(url: str, session: requests.Session, rate_limiter: RateLimiter) -> Optional[Article]:
    """
    Fetch and parse a single article. Returns Article object or None.
    """
    # Check if already scraped
    if is_url_scraped(url):
        logger.debug(f"Already scraped: {url}")
        return None
    
    rate_limiter.wait()
    
    status_code, html, final_url = fetch_article(url, session)
    
    if status_code == 404:
        logger.debug(f"404: {url}")
        failed = FailedUrl(
            url=url,
            source='crawler',
            error_code=404,
            error_message="Page not found"
        )
        save_failed_url(failed)
        update_url_status(url, 'failed')
        return None
    
    if status_code == 0 or not html:
        logger.warning(f"Failed to fetch {url} (status: {status_code})")
        failed = FailedUrl(
            url=url,
            source='crawler',
            error_code=status_code,
            error_message=f"HTTP error: {status_code}"
        )
        save_failed_url(failed)
        update_url_status(url, 'failed')
        return None
    
    if status_code != 200:
        logger.warning(f"Status {status_code} for {url}")
        failed = FailedUrl(
            url=url,
            source='crawler',
            error_code=status_code,
            error_message=f"HTTP {status_code}"
        )
        save_failed_url(failed)
        update_url_status(url, 'failed')
        return None
    
    # Parse the article
    article = parse_article(final_url if final_url != url else url, html)
    
    # If redirected to a new URL, also note original
    if final_url != url:
        article.url = url  # Keep original URL
        if not article.canonical_url:
            article.canonical_url = final_url
    
    return article


def save_scraped_article(article: Article) -> bool:
    """Save article to database with all related data"""
    if not article:
        return False
    
    # Save main article
    article_id = save_article(article)
    
    if article_id is None:
        logger.error(f"Failed to save article: {article.url}")
        return False
    
    # Save tags
    if article.tags:
        save_article_tags(article_id, article.tags)
    
    # Save media (we need to re-parse for full MediaItem objects)
    # This is simplified - in full version we'd pass MediaItems from parser
    media_items = []
    for idx, img_url in enumerate(article.images):
        media_items.append(MediaItem(
            article_id=article_id,
            media_type='image',
            url=img_url,
            is_main=(idx == 0 and img_url == article.main_image_url),
            position=idx
        ))
    
    for idx, vid_url in enumerate(article.videos):
        media_items.append(MediaItem(
            article_id=article_id,
            media_type='video',
            url=vid_url,
            position=idx
        ))
    
    if media_items:
        save_article_media(article_id, media_items)
    
    return True


def run_scraping_batch(
    urls: List[str],
    session: requests.Session,
    rate_limiter: RateLimiter,
    progress_callback: Optional[Callable] = None
) -> dict:
    """
    Scrape a batch of URLs. Returns statistics.
    """
    stats = {'scraped': 0, 'failed': 0, 'skipped': 0}
    
    for idx, url in enumerate(urls):
        try:
            article = scrape_article(url, session, rate_limiter)
            
            if article is None:
                if is_url_scraped(url):
                    stats['skipped'] += 1
                    update_url_status(url, 'scraped')
                else:
                    stats['failed'] += 1
                continue
            
            success = save_scraped_article(article)
            
            if success:
                if article.status == 'success':
                    stats['scraped'] += 1
                    update_url_status(url, 'scraped')
                    logger.debug(f"✓ Scraped: {article.title[:60] if article.title else 'No title'} | {url}")
                else:
                    stats['failed'] += 1
                    update_url_status(url, 'failed')
                    logger.debug(f"✗ Failed: {article.error_message} | {url}")
            else:
                stats['failed'] += 1
            
            if progress_callback:
                progress_callback(idx + 1, len(urls), stats)
            
            # Periodic checkpoint logging
            if (idx + 1) % 100 == 0:
                log = ScrapingLog(
                    session_id=SESSION_ID,
                    event_type='checkpoint',
                    message=f"Processed {idx + 1}/{len(urls)} URLs",
                    urls_scraped=stats['scraped'],
                    urls_failed=stats['failed']
                )
                save_scraping_log(log)
                logger.info(f"Checkpoint: {idx+1}/{len(urls)} | ✓{stats['scraped']} ✗{stats['failed']} ⟳{stats['skipped']}")
        
        except KeyboardInterrupt:
            logger.info("Interrupted by user. Saving checkpoint...")
            log = ScrapingLog(
                session_id=SESSION_ID,
                event_type='interrupted',
                message=f"User interrupted at {idx + 1}/{len(urls)}",
                urls_scraped=stats['scraped'],
                urls_failed=stats['failed']
            )
            save_scraping_log(log)
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error processing {url}: {e}")
            stats['failed'] += 1
    
    return stats


def run_full_scrape(
    batch_size: int = 50,
    min_delay: float = 0.5,
    max_delay: float = 1.5,
    progress_callback: Optional[Callable] = None
) -> dict:
    """
    Main scraping loop. Processes all pending URLs in batches.
    Supports resuming from where it left off.
    """
    session = create_session()
    rate_limiter = RateLimiter(min_delay=min_delay, max_delay=max_delay)
    
    # Log start
    log = ScrapingLog(
        session_id=SESSION_ID,
        event_type='started',
        message='Scraping session started'
    )
    save_scraping_log(log)
    
    total_stats = {'scraped': 0, 'failed': 0, 'skipped': 0}
    start_time = time.time()
    
    try:
        while True:
            # Get next batch of pending URLs
            pending = get_pending_urls(limit=batch_size)
            
            if not pending:
                logger.info("No more pending URLs. Scraping complete!")
                break
            
            urls = [p['url'] for p in pending]
            logger.info(f"Processing batch of {len(urls)} URLs...")
            
            batch_stats = run_scraping_batch(urls, session, rate_limiter, progress_callback)
            
            total_stats['scraped'] += batch_stats['scraped']
            total_stats['failed'] += batch_stats['failed']
            total_stats['skipped'] += batch_stats['skipped']
            
            elapsed = time.time() - start_time
            db_stats = get_stats()
            logger.info(
                f"Progress: ✓{total_stats['scraped']} scraped, "
                f"✗{total_stats['failed']} failed, "
                f"⟳{db_stats.get('pending_count', 0)} pending | "
                f"Elapsed: {elapsed:.0f}s"
            )
    
    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user.")
    
    finally:
        elapsed = time.time() - start_time
        log = ScrapingLog(
            session_id=SESSION_ID,
            event_type='completed',
            message=f"Session completed in {elapsed:.0f}s",
            urls_scraped=total_stats['scraped'],
            urls_failed=total_stats['failed']
        )
        save_scraping_log(log)
    
    total_stats['elapsed_seconds'] = time.time() - start_time
    return total_stats

