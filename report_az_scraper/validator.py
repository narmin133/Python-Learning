"""
validator.py - Data quality validation for scraped articles
"""
import re
import logging
from datetime import datetime
from typing import List, Dict, Any
from database import get_connection, get_stats

logger = logging.getLogger(__name__)


def validate_url(url: str) -> bool:
    """Validate URL format"""
    if not url:
        return False
    pattern = re.compile(
        r'^https?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return bool(pattern.match(url))


def validate_date(date_str: str) -> bool:
    """Check if date string is valid"""
    if not date_str:
        return False
    try:
        datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return True
    except (ValueError, AttributeError):
        return False


def run_validation() -> Dict[str, Any]:
    """
    Run comprehensive data quality checks on scraped articles.
    Returns a report dict.
    """
    conn = get_connection()
    report = {}
    
    try:
        cursor = conn.cursor()
        
        # Total articles
        cursor.execute("SELECT COUNT(*) FROM articles WHERE status='success'")
        total = cursor.fetchone()[0]
        report['total_articles'] = total
        
        if total == 0:
            logger.warning("No articles found in database!")
            return report
        
        # Missing titles
        cursor.execute("SELECT COUNT(*) FROM articles WHERE (title IS NULL OR title = '') AND status='success'")
        missing_titles = cursor.fetchone()[0]
        report['missing_titles'] = missing_titles
        report['missing_titles_pct'] = round(missing_titles / total * 100, 2) if total > 0 else 0
        
        # Missing dates
        cursor.execute("SELECT COUNT(*) FROM articles WHERE published_at IS NULL AND status='success'")
        missing_dates = cursor.fetchone()[0]
        report['missing_dates'] = missing_dates
        report['missing_dates_pct'] = round(missing_dates / total * 100, 2) if total > 0 else 0
        
        # Missing content
        cursor.execute("SELECT COUNT(*) FROM articles WHERE (content IS NULL OR content = '' OR length(content) < 50) AND status='success'")
        missing_content = cursor.fetchone()[0]
        report['missing_content'] = missing_content
        report['missing_content_pct'] = round(missing_content / total * 100, 2) if total > 0 else 0
        
        # Incomplete articles
        cursor.execute("SELECT COUNT(*) FROM articles WHERE is_incomplete=1 AND status='success'")
        incomplete = cursor.fetchone()[0]
        report['incomplete_articles'] = incomplete
        
        # Invalid URLs
        cursor.execute("SELECT url FROM articles WHERE status='success'")
        invalid_urls = 0
        for row in cursor.fetchall():
            if not validate_url(row[0]):
                invalid_urls += 1
        report['invalid_urls'] = invalid_urls
        
        # Short content (< 200 chars)
        cursor.execute("SELECT COUNT(*) FROM articles WHERE content_length < 200 AND content_length > 0 AND status='success'")
        short_content = cursor.fetchone()[0]
        report['short_content'] = short_content
        
        # Articles with images
        cursor.execute("SELECT COUNT(DISTINCT article_id) FROM article_media WHERE media_type='image'")
        articles_with_images = cursor.fetchone()[0]
        report['articles_with_images'] = articles_with_images
        
        # Articles with tags
        cursor.execute("SELECT COUNT(DISTINCT article_id) FROM article_tags")
        articles_with_tags = cursor.fetchone()[0]
        report['articles_with_tags'] = articles_with_tags
        
        # Date range
        cursor.execute("SELECT MIN(published_at), MAX(published_at) FROM articles WHERE published_at IS NOT NULL AND status='success'")
        row = cursor.fetchone()
        report['oldest_article'] = row[0]
        report['newest_article'] = row[1]
        
        # Articles by category
        cursor.execute("""
            SELECT category, COUNT(*) as cnt 
            FROM articles 
            WHERE status='success' AND category IS NOT NULL
            GROUP BY category 
            ORDER BY cnt DESC
            LIMIT 20
        """)
        report['top_categories'] = [{'category': row[0], 'count': row[1]} for row in cursor.fetchall()]
        
        # Articles by year
        cursor.execute("""
            SELECT substr(published_at, 1, 4) as year, COUNT(*) as cnt 
            FROM articles 
            WHERE status='success' AND published_at IS NOT NULL
            GROUP BY year
            ORDER BY year
        """)
        report['articles_by_year'] = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Failed URLs
        cursor.execute("SELECT COUNT(*) FROM failed_urls")
        report['failed_urls'] = cursor.fetchone()[0]
        
        # Success rate
        cursor.execute("SELECT COUNT(*) FROM discovered_urls")
        total_discovered = cursor.fetchone()[0]
        report['total_discovered'] = total_discovered
        report['success_rate'] = round(total / total_discovered * 100, 2) if total_discovered > 0 else 0
        
        # Completeness score
        completeness = 100.0
        if missing_titles > 0:
            completeness -= (missing_titles / total * 20)
        if missing_dates > 0:
            completeness -= (missing_dates / total * 20)
        if missing_content > 0:
            completeness -= (missing_content / total * 30)
        report['data_completeness_score'] = round(max(0, completeness), 2)
        
        # Overall quality assessment
        issues = []
        if missing_titles > total * 0.05:
            issues.append(f"High rate of missing titles: {missing_titles} ({report['missing_titles_pct']}%)")
        if missing_dates > total * 0.10:
            issues.append(f"High rate of missing dates: {missing_dates} ({report['missing_dates_pct']}%)")
        if missing_content > total * 0.10:
            issues.append(f"High rate of missing content: {missing_content} ({report['missing_content_pct']}%)")
        
        report['issues'] = issues
        report['validation_passed'] = len(issues) == 0
        
    finally:
        conn.close()
    
    return report


def print_validation_report(report: Dict):
    """Print a formatted validation report"""
    print("\n" + "=" * 60)
    print("DATA QUALITY VALIDATION REPORT")
    print("=" * 60)
    
    print(f"\n📊 Total articles: {report.get('total_articles', 0):,}")
    print(f"📊 Total discovered: {report.get('total_discovered', 0):,}")
    print(f"📊 Success rate: {report.get('success_rate', 0)}%")
    print(f"📊 Data completeness: {report.get('data_completeness_score', 0)}%")
    
    print(f"\n⚠️  Missing titles: {report.get('missing_titles', 0)} ({report.get('missing_titles_pct', 0)}%)")
    print(f"⚠️  Missing dates: {report.get('missing_dates', 0)} ({report.get('missing_dates_pct', 0)}%)")
    print(f"⚠️  Missing content: {report.get('missing_content', 0)} ({report.get('missing_content_pct', 0)}%)")
    print(f"⚠️  Incomplete articles: {report.get('incomplete_articles', 0)}")
    print(f"⚠️  Short content (<200 chars): {report.get('short_content', 0)}")
    
    print(f"\n🖼️  Articles with images: {report.get('articles_with_images', 0)}")
    print(f"🏷️  Articles with tags: {report.get('articles_with_tags', 0)}")
    print(f"❌ Failed URLs: {report.get('failed_urls', 0)}")
    
    if report.get('oldest_article'):
        print(f"\n📅 Oldest article: {report.get('oldest_article')}")
        print(f"📅 Newest article: {report.get('newest_article')}")
    
    if report.get('articles_by_year'):
        print("\n📅 Articles by year:")
        for year, count in sorted(report['articles_by_year'].items()):
            print(f"   {year}: {count:,}")
    
    if report.get('top_categories'):
        print("\n📁 Top categories:")
        for cat in report['top_categories'][:10]:
            print(f"   {cat['category']}: {cat['count']:,}")
    
    if report.get('issues'):
        print("\n🚨 Issues found:")
        for issue in report['issues']:
            print(f"   - {issue}")
    else:
        print("\n✅ No major issues found")
    
    print("=" * 60)

