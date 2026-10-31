"""
fast_scraper.py - Yüksək məhsuldarlıqlı, çoxaxınlı (multi-threaded) scraping sistemi
- Çoxaxınlı paralel yükləmə (ThreadPoolExecutor - 5-10 worker)
- Rate limiting və avtomatik retry mexanizmi (exponential backoff)
- Checkpoint dəstəyi (qaldığı yerdən davam etmə)
- Real-time irəliləyiş statistikası və loglama
- SQLite WAL rejimində təhlükəsiz tranzaksiyalar
"""
import sys
import os
import time
import random
import logging
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from database import (
    init_database, get_pending_urls, get_stats, update_url_status,
    save_article, save_article_tags, save_article_media, save_failed_url
)
from article_parser import parse_article
from models import Article, FailedUrl, MediaItem

Path("output/logs").mkdir(parents=True, exist_ok=True)
log_file = f"output/logs/fast_scrape_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'az,en-US;q=0.7,en;q=0.3',
}


def create_session():
    s = requests.Session()
    s.headers.update(HEADERS)
    adapter = requests.adapters.HTTPAdapter(
        pool_connections=20,
        pool_maxsize=20,
        max_retries=requests.adapters.Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
    )
    s.mount('https://', adapter)
    s.mount('http://', adapter)
    return s


def process_single_url(session, url: str) -> tuple:
    """Fetch and parse single article"""
    try:
        time.sleep(random.uniform(0.1, 0.4))  # Polite delay per thread
        resp = session.get(url, timeout=20, allow_redirects=True)
        resp.encoding = 'utf-8'
        
        if resp.status_code == 404:
            return url, False, 404, "Page Not Found", None
        
        if resp.status_code != 200:
            return url, False, resp.status_code, f"HTTP {resp.status_code}", None
        
        article = parse_article(url, resp.text)
        return url, (article.status == 'success'), resp.status_code, article.error_message, article
        
    except requests.exceptions.Timeout:
        return url, False, 0, "Timeout", None
    except Exception as e:
        return url, False, 0, str(e)[:200], None


def save_article_data(article: Article):
    """Save article, tags, and media to database"""
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


def run_scraper(max_workers: int = 5, batch_size: int = 50, max_articles: int = None):
    init_database()
    stats = get_stats()
    
    total_in_db = stats.get('total_discovered', 0)
    pending_total = stats.get('pending_count', 0)
    already_scraped = stats.get('total_scraped', 0)
    
    print("=" * 60)
    print("REPORT.AZ FAST MULTI-THREADED SCRAPER")
    print(f"Cəmi aşkar edilmiş xəbər URL-ləri: {total_in_db:,}")
    print(f"Əvvəlcədən toplanmış xəbərlər:      {already_scraped:,}")
    print(f"Gözləyən xəbərlər:                 {pending_total:,}")
    print(f"İşçi sayı (Workers):               {max_workers}")
    print(f"Toplu ölçüsü (Batch size):         {batch_size}")
    if max_articles:
        print(f"Hədəf limit:                       {max_articles:,}")
    print("=" * 60)
    
    session = create_session()
    
    total_processed = 0
    total_success = 0
    total_failed = 0
    start_time = time.time()
    last_log_time = start_time
    
    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            while True:
                if max_articles and total_success >= max_articles:
                    logger.info(f"Hədəf saya çatıldı: {total_success:,} xəbər!")
                    break
                    
                pending = get_pending_urls(limit=batch_size)
                if not pending:
                    logger.info("Bütün gözləyən URL-lər tamamlandı!")
                    break
                    
                urls_to_process = [p['url'] for p in pending]
                
                # Submit jobs
                future_to_url = {
                    executor.submit(process_single_url, session, url): url 
                    for url in urls_to_process
                }
                
                for future in as_completed(future_to_url):
                    url, success, status_code, err_msg, article = future.result()
                    total_processed += 1
                    
                    if success and article:
                        save_article_data(article)
                        update_url_status(url, 'scraped')
                        total_success += 1
                    else:
                        save_failed_url(FailedUrl(
                            url=url,
                            source='crawler',
                            error_code=status_code,
                            error_message=err_msg
                        ))
                        update_url_status(url, 'failed')
                        total_failed += 1
                        
                    now = time.time()
                    if total_processed % 25 == 0 or (now - last_log_time) >= 15:
                        elapsed = now - start_time
                        speed = total_processed / elapsed if elapsed > 0 else 0
                        logger.info(
                            f"[İrəliləyiş] Uğurlu: {total_success:,} | Uğursuz: {total_failed:,} | "
                            f"Sürət: {speed:.1f} xəbər/san | Müddət: {elapsed:.0f}s"
                        )
                        last_log_time = now
                        
                    if max_articles and total_success >= max_articles:
                        break
                        
    except KeyboardInterrupt:
        logger.info("\nİstifadəçi tərəfindən dayandırıldı! İrəliləyiş bazada saxlanıldı.")
    finally:
        elapsed = time.time() - start_time
        final_stats = get_stats()
        print("\n" + "=" * 60)
        print("SCRAPING İCRA NƏTİCƏSİ")
        print("=" * 60)
        print(f"Cəmi işlənən:          {total_processed:,}")
        print(f"Uğurla yazılan:        {total_success:,}")
        print(f"Uğursuz:               {total_failed:,}")
        print(f"Bazadakı cəmi xəbər:   {final_stats.get('total_scraped', 0):,}")
        print(f"Bazada qalan URL-lər:  {final_stats.get('pending_count', 0):,}")
        print(f"Ümumi vaxt:            {elapsed:.1f} saniyə")
        print("=" * 60)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Report.az Fast Scraper')
    parser.add_argument('--workers', type=int, default=6, help='Worker sayı')
    parser.add_argument('--batch-size', type=int, default=60, help='Batch ölçüsü')
    parser.add_argument('--limit', type=int, default=None, help='Maksimum toplanacaq xəbər sayı')
    args = parser.parse_args()
    
    run_scraper(max_workers=args.workers, batch_size=args.batch_size, max_articles=args.limit)

