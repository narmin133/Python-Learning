"""
run_scrape.py - Main scraping runner
Discovers URLs (if not already done) and scrapes all articles.
Supports resume from checkpoint.
"""
import sys
import os
import time

os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import logging
import requests
from datetime import datetime
from pathlib import Path

# Setup
Path("output/logs").mkdir(parents=True, exist_ok=True)
log_file = f"output/logs/scrape_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)

from database import init_database, get_pending_urls, get_stats, update_url_status, save_failed_url
from article_parser import parse_article
from models import Article, FailedUrl, MediaItem
from database import save_article, save_article_tags, save_article_media

# Configuration
MIN_DELAY = 0.4       # seconds between requests
MAX_DELAY = 1.0       # max random delay
BATCH_SIZE = 100      # process in batches
LOG_EVERY = 50        # log progress every N articles


def create_session():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'az,en;q=0.5',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    })
    adapter = requests.adapters.HTTPAdapter(
        max_retries=requests.adapters.Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
    )
    session.mount('https://', adapter)
    return session


def save_full_article(article: Article) -> bool:
    """Save article with all related data"""
    article_id = save_article(article)
    if article_id is None:
        return False
    
    if article.tags:
        save_article_tags(article_id, article.tags)
    
    media_items = []
    for idx, img_url in enumerate(article.images):
        media_items.append(MediaItem(
            article_id=article_id,
            media_type='image',
            url=img_url,
            is_main=(idx == 0),
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


def scrape_all():
    """Main scraping loop - processes all pending URLs"""
    init_database()
    session = create_session()
    
    total_scraped = 0
    total_failed = 0
    total_skipped = 0
    start_time = time.time()
    last_log_time = start_time
    
    print("\n" + "=" * 60)
    print("SCRAPING STARTED")
    print(f"Log: {log_file}")
    print("=" * 60)
    
    # Check initial stats
    stats = get_stats()
    total_pending = stats.get('pending_count', 0)
    total_in_db = stats.get('total_discovered', 0)
    print(f"\nTotal URLs in DB: {total_in_db:,}")
    print(f"Pending to scrape: {total_pending:,}")
    print(f"Already scraped: {stats.get('total_scraped', 0):,}")
    
    if total_pending == 0:
        print("\nNo pending URLs! Run discover first.")
        return
    
    print(f"\nStarting... (Press Ctrl+C to stop, progress is saved)")
    print("-" * 60)
    
    try:
        import random
        
        while True:
            # Get next batch
            pending = get_pending_urls(limit=BATCH_SIZE)
            
            if not pending:
                logger.info("All URLs processed!")
                break
            
            for item in pending:
                url = item['url']
                
                try:
                    # Random delay
                    delay = random.uniform(MIN_DELAY, MAX_DELAY)
                    time.sleep(delay)
                    
                    # Fetch
                    try:
                        resp = session.get(url, timeout=25, allow_redirects=True)
                        status_code = resp.status_code
                        html = resp.text
                        final_url = str(resp.url)
                    except requests.exceptions.Timeout:
                        logger.warning(f"Timeout: {url}")
                        save_failed_url(FailedUrl(url=url, source='scraper', error_code=0, error_message='Timeout'))
                        update_url_status(url, 'failed')
                        total_failed += 1
                        continue
                    except Exception as e:
                        logger.warning(f"Connection error {url}: {e}")
                        save_failed_url(FailedUrl(url=url, source='scraper', error_code=0, error_message=str(e)[:200]))
                        update_url_status(url, 'failed')
                        total_failed += 1
                        continue
                    
                    if status_code == 404:
                        save_failed_url(FailedUrl(url=url, source='scraper', error_code=404, error_message='Not found'))
                        update_url_status(url, 'failed')
                        total_failed += 1
                        continue
                    
                    if status_code != 200:
                        save_failed_url(FailedUrl(url=url, source='scraper', error_code=status_code, error_message=f'HTTP {status_code}'))
                        update_url_status(url, 'failed')
                        total_failed += 1
                        continue
                    
                    # Parse
                    article = parse_article(url, html)
                    
                    # Save
                    save_full_article(article)
                    update_url_status(url, 'scraped')
                    
                    if article.status == 'success':
                        total_scraped += 1
                    else:
                        total_failed += 1
                        save_failed_url(FailedUrl(
                            url=url,
                            source='scraper',
                            error_message=article.error_message or 'Parse failed'
                        ))
                    
                    # Progress logging
                    now = time.time()
                    processed = total_scraped + total_failed
                    if processed % LOG_EVERY == 0 or (now - last_log_time) > 60:
                        elapsed = now - start_time
                        rate = processed / elapsed if elapsed > 0 else 0
                        remaining_pending = get_stats().get('pending_count', 0)
                        eta_sec = remaining_pending / rate if rate > 0 else 0
                        eta_min = eta_sec / 60
                        
                        logger.info(
                            f"Progress: {processed:,} processed "
                            f"(+{total_scraped} ok, -{total_failed} fail) "
                            f"| {remaining_pending:,} pending "
                            f"| {rate:.1f}/s "
                            f"| ETA: {eta_min:.0f}min"
                        )
                        last_log_time = now
                
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    logger.error(f"Unexpected error for {url}: {e}")
                    total_failed += 1
    
    except KeyboardInterrupt:
        print("\n\nInterrupted! Progress saved to database.")
    
    finally:
        elapsed = time.time() - start_time
        final_stats = get_stats()
        
        print("\n" + "=" * 60)
        print("SCRAPING SESSION SUMMARY")
        print("=" * 60)
        print(f"  Duration:          {elapsed:.0f}s ({elapsed/3600:.2f}h)")
        print(f"  Scraped this run:  {total_scraped:,}")
        print(f"  Failed this run:   {total_failed:,}")
        print(f"  Total in DB:       {final_stats.get('total_scraped', 0):,}")
        print(f"  Still pending:     {final_stats.get('pending_count', 0):,}")
        print(f"  Log file:          {log_file}")
        print("=" * 60)


if __name__ == '__main__':
    scrape_all()

