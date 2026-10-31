"""
main.py - Main entry point for report.az scraper
"""
import os
import sys
import time
import logging
import argparse
from datetime import datetime
from pathlib import Path

os.environ['PYTHONIOENCODING'] = 'utf-8'
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

# Change to script directory so relative paths work
SCRIPT_DIR = Path(__file__).parent
os.chdir(SCRIPT_DIR)

# Setup logging
LOG_DIR = Path("output/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

log_filename = LOG_DIR / f"scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Rich console for pretty output
try:
    from rich.console import Console
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    from rich.panel import Panel
    from rich import print as rprint
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None


def print_banner():
    msg = """
╔══════════════════════════════════════════════════════════════╗
║         REPORT.AZ NEWS ARCHIVE SCRAPER                      ║
║         Bütün xəbər arxivinin toplanması                     ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(msg)


def mode_discover(args):
    """Discover all article URLs"""
    from database import init_database
    from discovery import discover_all_urls
    
    logger.info("MODE: DISCOVER - Finding all article URLs")
    init_database()
    
    max_pages = getattr(args, 'max_pages', 500)
    stats = discover_all_urls(max_category_pages=max_pages)
    
    print(f"\n✅ Discovery Complete!")
    print(f"   Total URLs found: {stats.get('total_new', 0):,}")
    print(f"   From sitemap:     {stats.get('sitemap', 0):,}")
    print(f"   From RSS:         {stats.get('rss', 0):,}")
    print(f"   From homepage:    {stats.get('homepage', 0):,}")
    print(f"   From categories:  {stats.get('categories', 0):,}")
    
    return stats


def mode_full(args):
    """Full scraping: discover + scrape all"""
    from database import init_database, get_stats
    from discovery import discover_all_urls
    from fast_scraper import run_scraper
    
    logger.info("MODE: FULL - Complete archive scraping")
    
    print_banner()
    print("Starting FULL scraping mode...")
    print(f"Log file: {log_filename}")
    
    # Step 1: Initialize DB
    logger.info("Initializing database...")
    init_database()
    
    db_stats = get_stats()
    total_pending = db_stats.get('pending_count', 0)
    
    # Step 2: Discover URLs if DB is empty
    if total_pending == 0 and db_stats.get('total_scraped', 0) == 0:
        logger.info("\n[PHASE 1] Discovering all URLs...")
        disc_stats = discover_all_urls()
        db_stats = get_stats()
        total_pending = db_stats.get('pending_count', 0)
    
    print(f"\n✅ Ready to scrape: {total_pending:,} articles pending in database")
    
    # Step 3: Fast Multi-threaded Scrape
    logger.info("\n[PHASE 2] Scraping articles...")
    start_time = time.time()
    
    workers = getattr(args, 'workers', 6)
    batch_size = getattr(args, 'batch_size', 50)
    limit = getattr(args, 'limit', None)
    
    run_scraper(max_workers=workers, batch_size=batch_size, max_articles=limit)
    elapsed = time.time() - start_time
    
    # Step 4: Export
    logger.info("\n[PHASE 3] Exporting data...")
    from exporter import export_all
    export_all()
    
    # Step 5: Validate
    logger.info("\n[PHASE 4] Validating data...")
    from validator import run_validation, print_validation_report
    val_report = run_validation()
    print_validation_report(val_report)


def mode_incremental(args):
    """Incremental scraping: only new articles and refresh exports"""
    import re
    import xml.etree.ElementTree as ET
    from database import init_database, add_discovered_urls, is_url_discovered, is_url_scraped, get_connection
    from models import DiscoveredUrl
    from fast_scraper import run_scraper
    from exporter import export_all
    from discovery import HEADERS, normalize_url, is_article_url
    import requests
    
    logger.info("MODE: INCREMENTAL - Fetching newest articles and refreshing")
    init_database()
    
    session = requests.Session()
    session.headers.update(HEADERS)
    
    print("\n" + "=" * 60)
    print("YENİ XƏBƏRLƏRİN YOXLANILMASI VƏ YENİLƏNMƏSİ (REFRESH)")
    print("=" * 60)
    
    fresh_urls = []
    
    # 1. Check Google News sitemap (son 48 saatın canlı xəbərləri)
    try:
        r = session.get("https://report.az/news-sitemap.xml", timeout=20)
        if r.status_code == 200:
            urls = re.findall(r'<loc>([^<]+)</loc>', r.text)
            print(f"📡 news-sitemap.xml-dən tapıldı: {len(urls)} son xəbər")
            fresh_urls.extend(urls)
    except Exception as e:
        logger.warning(f"news-sitemap xətası: {e}")
        
    # 2. Check sitemap-posts.xml
    try:
        r = session.get("https://report.az/sitemap-posts.xml", timeout=20)
        if r.status_code == 200:
            urls = re.findall(r'<loc>([^<]+)</loc>', r.text)
            print(f"📡 sitemap-posts.xml-dən tapıldı: {len(urls)} son xəbər")
            fresh_urls.extend(urls)
    except Exception as e:
        logger.warning(f"sitemap-posts xətası: {e}")

    # 3. Check Homepage
    try:
        from discovery import discover_from_homepage
        hp_articles, _ = discover_from_homepage(session)
        print(f"📡 Ana səhifədən tapıldı: {len(hp_articles)} aktiv xəbər")
        fresh_urls.extend(hp_articles)
    except Exception as e:
        logger.warning(f"Homepage xətası: {e}")

    # Unikallaşdırma və filtrləmə
    unique_fresh = list(set([normalize_url(u.strip()) for u in fresh_urls if u and is_article_url(u)]))
    print(f"🔍 Cəmi yoxlanılan unikal son xəbər URL-i: {len(unique_fresh)}")

    new_urls_to_scrape = []
    conn = get_connection()
    try:
        cursor = conn.cursor()
        for u in unique_fresh:
            # Check if not scraped yet
            cursor.execute("SELECT id FROM articles WHERE url = ? AND status = 'success'", (u,))
            if not cursor.fetchone():
                # Add to DB queue with highest priority 100
                cursor.execute("""
                    INSERT INTO discovered_urls (url, source, discovered_at, status, priority)
                    VALUES (?, 'refresh_incremental', datetime('now'), 'pending', 100)
                    ON CONFLICT(url) DO UPDATE SET priority = 100, status = 'pending'
                    WHERE status != 'scraped'
                """, (u,))
                new_urls_to_scrape.append(u)
        conn.commit()
    finally:
        conn.close()

    print(f"⚡ Toplanacaq yeni/gözləyən son xəbər sayı: {len(new_urls_to_scrape)}")

    # Yeni xəbərləri scrape et
    limit = getattr(args, 'limit', None) or (len(new_urls_to_scrape) if new_urls_to_scrape else 50)
    workers = getattr(args, 'workers', 5)
    
    run_scraper(max_workers=workers, batch_size=30, max_articles=limit)

    # Nəticələri bütün formatlarda dərhal ixrac et
    print("\n📂 Fayllar yenilənir (articles.csv, articles.json, və s.)...")
    export_all()
    print("✅ Bütün məlumatlar və ixrac faylları uğurla yeniləndi (REFRESH TAMAMLANDI)!")


def mode_validate(args):
    """Validate scraped data quality"""
    from validator import run_validation, print_validation_report
    from deduplication import mark_duplicates, get_dedup_stats
    
    logger.info("MODE: VALIDATE - Data quality check")
    
    report = run_validation()
    print_validation_report(report)
    
    # Deduplication check
    dedup = get_dedup_stats()
    print(f"\n🔍 Deduplication:")
    print(f"   URL duplicates:   {dedup.get('url_duplicates', 0)}")
    print(f"   Title duplicates: {dedup.get('title_duplicates', 0)}")


def mode_export(args):
    """Export data to specified format"""
    from exporter import export_json, export_jsonl, export_csv, export_all, export_categories_json, export_failed_urls_csv, export_scraping_report
    
    fmt = getattr(args, 'format', 'all')
    logger.info(f"MODE: EXPORT - Format: {fmt}")
    
    if fmt == 'json':
        path = export_json()
        print(f"✅ Exported to: {path}")
    elif fmt == 'jsonl':
        path = export_jsonl()
        print(f"✅ Exported to: {path}")
    elif fmt == 'csv':
        path = export_csv()
        print(f"✅ Exported to: {path}")
    else:  # 'all'
        exported = export_all()
        print("✅ All formats exported:")
        for name, path in exported.items():
            print(f"   {path}")


def mode_stats(args):
    """Print statistics"""
    from database import get_stats, get_db_size
    from exporter import generate_scraping_report
    
    logger.info("MODE: STATS")
    
    report = generate_scraping_report()
    stats = report['statistics']
    
    print("\n" + "=" * 60)
    print("REPORT.AZ SCRAPING STATISTICS")
    print("=" * 60)
    print(f"\n📊 Total URLs discovered:  {stats.get('total_urls_discovered', 0):,}")
    print(f"✅ Successfully scraped:   {stats.get('total_urls_scraped_successfully', 0):,}")
    print(f"❌ Failed:                 {stats.get('total_urls_failed', 0):,}")
    print(f"⏳ Pending:                {stats.get('total_pending', 0):,}")
    print(f"📁 Categories:             {stats.get('total_categories', 0):,}")
    print(f"🖼️  Images collected:       {stats.get('total_images', 0):,}")
    print(f"🎥 Videos collected:       {stats.get('total_videos', 0):,}")
    print(f"📅 No date:                {stats.get('articles_without_date', 0):,}")
    print(f"⚠️  Incomplete:             {stats.get('articles_incomplete', 0):,}")
    
    date_range = report.get('date_range', {})
    if date_range.get('oldest_article'):
        print(f"\n📅 Oldest article: {date_range['oldest_article']}")
        print(f"📅 Newest article: {date_range['newest_article']}")
    
    db_info = report.get('database', {})
    print(f"\n💾 Database size: {db_info.get('size_mb', 0)} MB")
    
    if stats.get('success_rate_percent') is not None:
        print(f"\n📈 Success rate: {stats['success_rate_percent']}%")
    
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description='report.az News Archive Scraper',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  discover    - Find all article URLs (does not scrape)
  full        - Full scraping: discover + scrape all articles
  incremental - Only scrape new articles (resume/update)
  validate    - Check data quality
  export      - Export data to files
  stats       - Show statistics

Examples:
  python main.py --mode discover
  python main.py --mode full
  python main.py --mode incremental
  python main.py --mode validate
  python main.py --mode export --format json
  python main.py --mode export --format csv
  python main.py --mode export --format all
  python main.py --mode stats
        """
    )
    
    parser.add_argument(
        '--mode',
        choices=['discover', 'full', 'incremental', 'validate', 'export', 'stats'],
        default='stats',
        help='Operation mode'
    )
    
    parser.add_argument(
        '--format',
        choices=['json', 'jsonl', 'csv', 'all'],
        default='all',
        help='Export format (for export mode)'
    )
    
    parser.add_argument(
        '--max-pages',
        type=int,
        default=500,
        dest='max_pages',
        help='Maximum category pages to crawl (default: 500)'
    )
    
    parser.add_argument(
        '--delay',
        type=float,
        default=0.5,
        help='Minimum delay between requests in seconds (default: 0.5)'
    )
    
    parser.add_argument(
        '--batch-size',
        type=int,
        default=50,
        dest='batch_size',
        help='Number of URLs to process per batch (default: 50)'
    )
    
    parser.add_argument(
        '--workers',
        type=int,
        default=5,
        help='Paralel sorğu axınlarının sayı (default: 5)'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Maksimum toplanacaq xəbər sayı (default: hamısı)'
    )
    
    args = parser.parse_args()
    
    print_banner()
    logger.info(f"Starting scraper in mode: {args.mode}")
    logger.info(f"Working directory: {os.getcwd()}")
    logger.info(f"Log file: {log_filename}")
    
    try:
        if args.mode == 'discover':
            mode_discover(args)
        elif args.mode == 'full':
            mode_full(args)
        elif args.mode == 'incremental':
            mode_incremental(args)
        elif args.mode == 'validate':
            mode_validate(args)
        elif args.mode == 'export':
            mode_export(args)
        elif args.mode == 'stats':
            mode_stats(args)
        else:
            parser.print_help()
    
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user. Progress has been saved.")
        logger.info("Scraper interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

