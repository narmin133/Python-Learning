"""
discovery.py - Discover all news article URLs from report.az
"""
import re
import time
import logging
from datetime import datetime
from typing import Set, List, Dict, Tuple
from urllib.parse import urljoin, urlparse, urlunparse
import requests
from bs4 import BeautifulSoup

from models import DiscoveredUrl, Category
from database import add_discovered_urls, is_url_discovered, save_category, get_stats

logger = logging.getLogger(__name__)

BASE_URL = "https://report.az"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'az,en-US;q=0.7,en;q=0.3',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

# Known category patterns for report.az
CATEGORY_SLUGS = [
    'azerbaycan', 'dunya', 'iqtisadiyyat', 'idman', 'texnologiya',
    'hadise', 'sosial', 'siyaset', 'kultur', 'elm', 'sagliq',
    'region', 'muhit', 'hucum', 'muharibe', 'diplomatiya',
    'az', 'world', 'economy', 'sport', 'technology', 'society',
    'health', 'culture', 'science', 'politics', 'society',
    'crime', 'accident', 'environment', 'military',
    # Russian categories  
    'azerbajdzhan', 'mir', 'ekonomika', 'sport', 'tehnologii',
    # English categories
    'news', 'politics', 'economy', 'sports', 'society',
]

# RSS feed patterns to check
RSS_PATTERNS = [
    "/feed/", "/rss/", "/rss.xml", "/feed.xml",
    "/feed/rss/", "/index.rss", "/atom.xml",
    "/?feed=rss2", "/?feed=atom",
    "/rss/news/", "/rss/all/",
]


def normalize_url(url: str) -> str:
    """Normalize URL to avoid duplicates"""
    parsed = urlparse(url)
    # Remove trailing slash
    path = parsed.path.rstrip('/')
    if not path:
        path = '/'
    # Remove fragment
    normalized = urlunparse((
        parsed.scheme, parsed.netloc, path,
        '', parsed.query, ''
    ))
    return normalized


def is_article_url(url: str) -> bool:
    """Determine if a URL is likely an article URL"""
    parsed = urlparse(url)
    
    if 'report.az' not in parsed.netloc:
        return False
    
    path = parsed.path.strip('/')
    
    if not path:
        return False
    
    # Skip admin, API, and utility paths
    skip_prefixes = [
        'wp-', 'admin', 'api/', 'feed', 'rss', 'sitemap', 
        'static', 'media', 'uploads', 'images', 'img', 'css', 'js',
        'fonts', 'favicon', 'robots', 'search', 'axtaris',
        'login', 'register', 'password', 'account', 'user',
        'contact', 'haqqimizda', 'about', 'redirect',
        'tag/', 'teq/', '#',
    ]
    
    path_lower = path.lower()
    for prefix in skip_prefixes:
        if path_lower.startswith(prefix):
            return False
    
    # Skip if it's a category listing page (e.g., /category/ with no numeric ID)
    # Article URLs usually contain a numeric ID or date component
    parts = [p for p in path.split('/') if p]
    
    # Check for numeric component (article ID)
    has_numeric = any(p.isdigit() or re.match(r'^\d+-', p) for p in parts)
    
    # Check for date pattern
    has_date = re.search(r'/\d{4}/\d{2}/', path) is not None
    
    # Long paths with slug-like components
    if len(parts) >= 2:
        last_part = parts[-1]
        # In report.az, article slugs are hyphenated phrases: e.g. /category/news-headline-slug
        if '-' in last_part and len(last_part) >= 10:
            return True
        if has_numeric or has_date or len(parts) >= 3:
            return True
    
    # Simple numeric ID at end
    if parts and parts[-1].isdigit():
        return True
    
    return False


def is_category_url(url: str) -> bool:
    """Determine if URL is a category/listing page"""
    parsed = urlparse(url)
    if 'report.az' not in parsed.netloc:
        return False
    
    path = parsed.path.strip('/')
    parts = [p for p in path.split('/') if p]
    
    # Single level paths are likely categories
    if len(parts) == 1 and not parts[0].isdigit():
        return True
    
    # Pagination patterns: /category/page/2/ or /category/?page=2
    if 'page' in path.lower() or parsed.query:
        return True
    
    return False


def fetch_page(url: str, session: requests.Session, timeout: int = 20) -> Tuple[int, str]:
    """Fetch a page with retry logic"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            resp = session.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
            return resp.status_code, resp.text
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                return 0, ""
        except Exception as e:
            logger.debug(f"Fetch error for {url}: {e}")
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                return 0, ""
    return 0, ""


def extract_urls_from_page(html: str, base_url: str) -> Tuple[List[str], List[str]]:
    """
    Extract article URLs and category URLs from a page.
    Returns (article_urls, category_urls)
    """
    article_urls = []
    category_urls = []
    
    try:
        soup = BeautifulSoup(html, 'lxml')
        
        for a in soup.find_all('a', href=True):
            href = a['href'].strip()
            
            if not href or href.startswith('#') or href.startswith('javascript:'):
                continue
            
            # Make absolute URL
            if href.startswith('//'):
                href = 'https:' + href
            elif href.startswith('/'):
                href = BASE_URL + href
            elif not href.startswith('http'):
                href = urljoin(base_url, href)
            
            # Normalize
            href = normalize_url(href)
            
            if 'report.az' not in href:
                continue
            
            if is_article_url(href):
                article_urls.append(href)
            elif is_category_url(href):
                category_urls.append(href)
        
    except Exception as e:
        logger.error(f"Error extracting URLs from {base_url}: {e}")
    
    return article_urls, category_urls


def discover_from_homepage(session: requests.Session) -> Tuple[List[str], List[Category]]:
    """Discover URLs from the homepage"""
    logger.info("Discovering from homepage...")
    
    status, html = fetch_page(BASE_URL, session)
    if status != 200:
        logger.error(f"Could not fetch homepage: status {status}")
        return [], []
    
    article_urls, category_urls_raw = extract_urls_from_page(html, BASE_URL)
    
    # Parse categories from navigation
    categories = []
    try:
        soup = BeautifulSoup(html, 'lxml')
        
        # Look for navigation menus
        nav_selectors = [
            ('nav', {}),
            ('ul', {'class': re.compile(r'menu|nav|header', re.I)}),
            ('div', {'class': re.compile(r'menu|navigation|nav', re.I)}),
            ('header', {}),
        ]
        
        for tag_name, attrs in nav_selectors:
            nav = soup.find(tag_name, attrs)
            if nav:
                for link in nav.find_all('a', href=True):
                    href = link['href']
                    if href.startswith('/'):
                        href = BASE_URL + href
                    
                    if not href.startswith(BASE_URL):
                        continue
                    
                    parts = urlparse(href).path.strip('/').split('/')
                    if len(parts) == 1 and parts[0] and not parts[0].isdigit():
                        name = clean_text(link.get_text())
                        slug = parts[0]
                        if name and slug and len(name) < 50:
                            cat = Category(
                                name=name,
                                slug=slug,
                                url=normalize_url(href)
                            )
                            categories.append(cat)
    except Exception as e:
        logger.error(f"Error parsing categories from homepage: {e}")
    
    logger.info(f"Homepage: {len(article_urls)} articles, {len(categories)} categories")
    return article_urls, categories


def clean_text(text: str) -> str:
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text).strip()


def discover_from_rss(session: requests.Session) -> List[str]:
    """Discover articles from RSS feeds"""
    article_urls = []
    
    for rss_path in RSS_PATTERNS:
        rss_url = BASE_URL + rss_path
        status, content = fetch_page(rss_url, session)
        
        if status != 200 or not content:
            continue
        
        # Parse RSS/Atom
        try:
            import xml.etree.ElementTree as ET
            content_clean = content
            for ns in ['xmlns="', "xmlns='", "xmlns:atom="]:
                content_clean = re.sub(r'xmlns(?::[a-zA-Z]+)?="[^"]*"', '', content_clean)
                content_clean = re.sub(r"xmlns(?::[a-zA-Z]+)?='[^']*'", '', content_clean)
            
            root = ET.fromstring(content_clean)
            
            for link in root.iter('link'):
                url = link.text or link.get('href', '')
                if url and 'report.az' in url and is_article_url(url.strip()):
                    article_urls.append(url.strip())
            
            for item_url in root.iter('guid'):
                url = item_url.text or ''
                if url and 'report.az' in url and is_article_url(url.strip()):
                    article_urls.append(url.strip())
                    
            logger.info(f"RSS {rss_url}: {len(article_urls)} articles")
            
        except Exception as e:
            logger.debug(f"RSS parse error for {rss_url}: {e}")
        
        time.sleep(0.5)
    
    return list(set(article_urls))


def discover_from_category(
    category_url: str, 
    session: requests.Session,
    max_pages: int = 500,
    delay: float = 0.5
) -> List[str]:
    """
    Crawl a category page and all its pagination to discover articles.
    Returns list of article URLs.
    """
    all_article_urls = []
    visited_pages = set()
    
    # Try different pagination patterns
    pagination_patterns = [
        lambda url, page: f"{url.rstrip('/')}/page/{page}/",
        lambda url, page: f"{url.rstrip('/')}/?page={page}",
        lambda url, page: f"{url.rstrip('/')}?page={page}",
        lambda url, page: f"{url.rstrip('/')}/page-{page}/",
    ]
    
    # First, fetch the base page
    status, html = fetch_page(category_url, session)
    if status != 200 or not html:
        return []
    
    article_urls, _ = extract_urls_from_page(html, category_url)
    all_article_urls.extend(article_urls)
    visited_pages.add(category_url)
    
    if not article_urls:
        return all_article_urls
    
    # Try to find pagination
    try:
        soup = BeautifulSoup(html, 'lxml')
        
        # Find max page number
        max_page_found = 1
        
        # Look for pagination links
        pag_selectors = [
            ('div', {'class': re.compile(r'pagination|pager|pages', re.I)}),
            ('nav', {'class': re.compile(r'pagination|pager', re.I)}),
            ('ul', {'class': re.compile(r'pagination|pager', re.I)}),
        ]
        
        for tag_name, attrs in pag_selectors:
            pag = soup.find(tag_name, attrs)
            if pag:
                for link in pag.find_all('a', href=True):
                    text = link.get_text().strip()
                    if text.isdigit():
                        max_page_found = max(max_page_found, int(text))
        
        # If we found pagination, use it
        if max_page_found > 1:
            logger.info(f"Category {category_url}: found {max_page_found} pages")
            max_page_found = min(max_page_found, max_pages)
        
    except Exception as e:
        logger.debug(f"Error finding pagination for {category_url}: {e}")
        max_page_found = 50  # Default: try 50 pages
    
    # Crawl pages using the most common pagination pattern
    page = 2
    consecutive_empty = 0
    
    while page <= max(max_page_found, 50) and consecutive_empty < 3:
        page_url = f"{category_url.rstrip('/')}/page/{page}/"
        
        if page_url in visited_pages:
            page += 1
            continue
        
        visited_pages.add(page_url)
        time.sleep(delay)
        
        status, html = fetch_page(page_url, session)
        
        if status == 404 or status == 0:
            # Try alternative pagination pattern
            page_url2 = f"{category_url.rstrip('/')}?page={page}"
            status2, html2 = fetch_page(page_url2, session)
            if status2 == 200 and html2:
                html = html2
                status = status2
            else:
                consecutive_empty += 1
                page += 1
                continue
        
        if status != 200:
            consecutive_empty += 1
            page += 1
            continue
        
        new_urls, _ = extract_urls_from_page(html, page_url)
        
        if not new_urls:
            consecutive_empty += 1
        else:
            consecutive_empty = 0
            all_article_urls.extend(new_urls)
            logger.debug(f"  Page {page}: {len(new_urls)} articles (total: {len(all_article_urls)})")
        
        page += 1
    
    return all_article_urls


def discover_all_urls(max_category_pages: int = 500) -> Dict[str, int]:
    """
    Main discovery function. Finds all article URLs through all methods.
    Returns statistics dict.
    """
    session = requests.Session()
    session.headers.update(HEADERS)
    
    all_discovered: Set[str] = set()
    stats = {'sitemap': 0, 'rss': 0, 'homepage': 0, 'categories': 0, 'total_new': 0}
    
    # ---- PHASE 1: Sitemap ----
    logger.info("=" * 60)
    logger.info("PHASE 1: Sitemap Discovery")
    logger.info("=" * 60)
    
    try:
        from sitemap_parser import get_all_sitemap_urls
        sitemap_urls, sitemap_sources = get_all_sitemap_urls()
        
        if sitemap_urls:
            new_discovered = []
            for url in sitemap_urls:
                url = normalize_url(url)
                if url not in all_discovered and not is_url_discovered(url):
                    all_discovered.add(url)
                    new_discovered.append(DiscoveredUrl(
                        url=url,
                        source='sitemap',
                        discovered_at=datetime.now(),
                        priority=10
                    ))
            
            added = add_discovered_urls(new_discovered)
            stats['sitemap'] = added
            logger.info(f"Sitemap: {len(sitemap_urls)} URLs found, {added} new added to DB")
    except Exception as e:
        logger.error(f"Sitemap discovery failed: {e}")
    
    # ---- PHASE 2: RSS Feeds ----
    logger.info("=" * 60)
    logger.info("PHASE 2: RSS Feed Discovery")
    logger.info("=" * 60)
    
    rss_urls = discover_from_rss(session)
    if rss_urls:
        new_discovered = []
        for url in rss_urls:
            url = normalize_url(url)
            if url not in all_discovered and not is_url_discovered(url):
                all_discovered.add(url)
                new_discovered.append(DiscoveredUrl(
                    url=url,
                    source='rss',
                    discovered_at=datetime.now(),
                    priority=8
                ))
        added = add_discovered_urls(new_discovered)
        stats['rss'] = added
        logger.info(f"RSS: {len(rss_urls)} URLs found, {added} new")
    
    # ---- PHASE 3: Homepage ----
    logger.info("=" * 60)
    logger.info("PHASE 3: Homepage Discovery")
    logger.info("=" * 60)
    
    hp_articles, hp_categories = discover_from_homepage(session)
    
    # Save categories
    for cat in hp_categories:
        save_category(cat)
    
    new_discovered = []
    for url in hp_articles:
        url = normalize_url(url)
        if url not in all_discovered and not is_url_discovered(url):
            all_discovered.add(url)
            new_discovered.append(DiscoveredUrl(
                url=url,
                source='homepage',
                discovered_at=datetime.now(),
                priority=5
            ))
    added = add_discovered_urls(new_discovered)
    stats['homepage'] = added
    
    # ---- PHASE 4: Category Pages ----
    logger.info("=" * 60)
    logger.info("PHASE 4: Category Page Discovery")
    logger.info("=" * 60)
    
    # Build list of categories to crawl
    categories_to_crawl = set()
    for cat in hp_categories:
        categories_to_crawl.add(cat.url)
    
    # Add known category slugs
    for slug in CATEGORY_SLUGS:
        cat_url = f"{BASE_URL}/{slug}/"
        categories_to_crawl.add(normalize_url(cat_url))
    
    cat_article_count = 0
    for idx, cat_url in enumerate(sorted(categories_to_crawl), 1):
        logger.info(f"Crawling category {idx}/{len(categories_to_crawl)}: {cat_url}")
        time.sleep(0.3)
        
        cat_urls = discover_from_category(cat_url, session, max_pages=max_category_pages)
        
        new_discovered = []
        for url in cat_urls:
            url = normalize_url(url)
            if url not in all_discovered and not is_url_discovered(url):
                all_discovered.add(url)
                new_discovered.append(DiscoveredUrl(
                    url=url,
                    source=f'category:{cat_url}',
                    discovered_at=datetime.now(),
                    priority=7
                ))
        
        added = add_discovered_urls(new_discovered)
        cat_article_count += added
        logger.info(f"  {cat_url}: {len(cat_urls)} articles found, {added} new")
    
    stats['categories'] = cat_article_count
    
    # ---- Final stats ----
    db_stats = get_stats()
    stats['total_new'] = db_stats.get('total_discovered', 0)
    
    logger.info("=" * 60)
    logger.info("DISCOVERY COMPLETE")
    logger.info(f"Total URLs in DB: {stats['total_new']}")
    logger.info(f"  From sitemap:   {stats['sitemap']}")
    logger.info(f"  From RSS:       {stats['rss']}")
    logger.info(f"  From homepage:  {stats['homepage']}")
    logger.info(f"  From categories:{stats['categories']}")
    logger.info("=" * 60)
    
    return stats

