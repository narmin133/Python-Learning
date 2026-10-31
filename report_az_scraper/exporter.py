"""
exporter.py - Export scraped data to various formats (JSON, JSONL, CSV, etc.)
"""
import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from database import get_connection, get_all_articles_ordered, get_db_size, get_stats

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("output")


def ensure_output_dir():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "logs").mkdir(exist_ok=True)


def get_categories() -> List[Dict]:
    """Get all categories from database"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM categories ORDER BY name")
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_failed_urls() -> List[Dict]:
    """Get all failed URLs"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM failed_urls ORDER BY last_attempt DESC")
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def article_to_export_dict(article: Dict) -> Dict:
    """Convert database article row to clean export dict"""
    # Parse JSON fields
    for field in ['tags', 'images', 'videos', 'related_articles']:
        if article.get(field):
            try:
                article[field] = json.loads(article[field])
            except (json.JSONDecodeError, TypeError):
                article[field] = []
        else:
            article[field] = []
    
    # Convert boolean
    article['is_incomplete'] = bool(article.get('is_incomplete', 0))
    
    return article


def export_json(order: str = 'desc') -> Path:
    """Export all articles to JSON file"""
    ensure_output_dir()
    
    articles = get_all_articles_ordered(order)
    articles = [article_to_export_dict(a) for a in articles]
    
    output_path = OUTPUT_DIR / "articles.json"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, indent=2, default=str)
    
    logger.info(f"Exported {len(articles)} articles to {output_path}")
    return output_path


def export_jsonl(order: str = 'desc') -> Path:
    """Export all articles to JSONL (JSON Lines) file"""
    ensure_output_dir()
    
    articles = get_all_articles_ordered(order)
    
    output_path = OUTPUT_DIR / "articles.jsonl"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for article in articles:
            article = article_to_export_dict(article)
            f.write(json.dumps(article, ensure_ascii=False, default=str) + '\n')
    
    logger.info(f"Exported {len(articles)} articles to {output_path}")
    return output_path


def export_csv(order: str = 'desc') -> Path:
    """Export all articles to CSV file"""
    ensure_output_dir()
    
    articles = get_all_articles_ordered(order)
    
    if not articles:
        logger.warning("No articles to export")
        return OUTPUT_DIR / "articles.csv"
    
    output_path = OUTPUT_DIR / "articles.csv"
    
    # Define CSV columns (exclude large/complex fields)
    csv_fields = [
        'id', 'url', 'canonical_url', 'title', 'subtitle', 'summary',
        'author', 'journalist', 'source', 'category', 'subcategory',
        'language', 'published_at', 'published_at_raw', 'updated_at',
        'scraped_at', 'main_image_url', 'meta_description', 'meta_keywords',
        'og_title', 'og_description', 'og_image', 'content_length',
        'is_incomplete', 'status'
    ]
    
    with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields, extrasaction='ignore')
        writer.writeheader()
        
        for article in articles:
            row = {field: article.get(field, '') for field in csv_fields}
            # Convert lists to string for CSV
            writer.writerow(row)
    
    logger.info(f"Exported {len(articles)} articles to {output_path}")
    return output_path


def export_categories_json() -> Path:
    """Export categories to JSON"""
    ensure_output_dir()
    
    categories = get_categories()
    output_path = OUTPUT_DIR / "categories.json"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(categories, f, ensure_ascii=False, indent=2, default=str)
    
    logger.info(f"Exported {len(categories)} categories to {output_path}")
    return output_path


def export_failed_urls_csv() -> Path:
    """Export failed URLs to CSV"""
    ensure_output_dir()
    
    failed = get_failed_urls()
    output_path = OUTPUT_DIR / "failed_urls.csv"
    
    if not failed:
        # Create empty file with headers
        with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['url', 'source', 'error_code', 'error_message', 'attempts', 'last_attempt'])
            writer.writeheader()
        return output_path
    
    with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=failed[0].keys(), extrasaction='ignore')
        writer.writeheader()
        writer.writerows(failed)
    
    logger.info(f"Exported {len(failed)} failed URLs to {output_path}")
    return output_path


def generate_scraping_report() -> Dict:
    """Generate comprehensive scraping report"""
    stats = get_stats()
    db_size = get_db_size()
    
    report = {
        'report_generated_at': datetime.now().isoformat(),
        'site': 'https://report.az',
        'statistics': {
            'total_urls_discovered': stats.get('total_discovered', 0),
            'total_urls_scraped_successfully': stats.get('total_scraped', 0),
            'total_urls_failed': stats.get('total_failed', 0),
            'total_pending': stats.get('pending_count', 0),
            'total_categories': stats.get('total_categories', 0),
            'total_images': stats.get('total_images', 0),
            'total_videos': stats.get('total_videos', 0),
            'articles_without_date': stats.get('no_date_count', 0),
            'articles_incomplete': stats.get('incomplete_count', 0),
        },
        'date_range': {
            'oldest_article': stats.get('oldest_article'),
            'newest_article': stats.get('newest_article'),
        },
        'database': {
            'path': 'output/report_az.db',
            'size_bytes': db_size,
            'size_mb': round(db_size / 1024 / 1024, 2),
        },
        'output_files': {
            'database': 'output/report_az.db',
            'articles_json': 'output/articles.json',
            'articles_jsonl': 'output/articles.jsonl',
            'articles_csv': 'output/articles.csv',
            'categories_json': 'output/categories.json',
            'failed_urls_csv': 'output/failed_urls.csv',
        }
    }
    
    # Calculate success rate
    total_disc = stats.get('total_discovered', 0)
    total_scraped = stats.get('total_scraped', 0)
    if total_disc > 0:
        report['statistics']['success_rate_percent'] = round(total_scraped / total_disc * 100, 2)
    
    return report


def export_scraping_report() -> Path:
    """Save scraping report to JSON"""
    ensure_output_dir()
    
    report = generate_scraping_report()
    output_path = OUTPUT_DIR / "scraping_report.json"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    
    logger.info(f"Scraping report saved to {output_path}")
    return output_path


def export_all(order: str = 'desc') -> Dict[str, Path]:
    """Export all data in all formats (default: desc - newest first)"""
    ensure_output_dir()
    
    logger.info("Starting full data export...")
    
    exported = {}
    
    try:
        exported['articles_json'] = export_json(order)
    except Exception as e:
        logger.error(f"JSON export failed: {e}")
    
    try:
        exported['articles_jsonl'] = export_jsonl(order)
    except Exception as e:
        logger.error(f"JSONL export failed: {e}")
    
    try:
        exported['articles_csv'] = export_csv(order)
    except Exception as e:
        logger.error(f"CSV export failed: {e}")
    
    try:
        exported['categories_json'] = export_categories_json()
    except Exception as e:
        logger.error(f"Categories export failed: {e}")
    
    try:
        exported['failed_urls_csv'] = export_failed_urls_csv()
    except Exception as e:
        logger.error(f"Failed URLs export failed: {e}")
    
    try:
        exported['scraping_report'] = export_scraping_report()
    except Exception as e:
        logger.error(f"Report export failed: {e}")
    
    logger.info("Export complete!")
    for name, path in exported.items():
        size = path.stat().st_size if path.exists() else 0
        logger.info(f"  {name}: {path} ({size:,} bytes)")
    
    return exported

