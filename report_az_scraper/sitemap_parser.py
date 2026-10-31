"""
sitemap_parser.py - Parse sitemaps for report.az
Saytın sitemap strukturu:
  - sitemap.xml -> sitemap indeksi (225 sitemap)
  - sitemap-posts-archive-YYYY-M-N.xml -> aylıq xəbər arxivləri (2014-dən bu günə qədər)
  - sitemap-posts.xml -> son xəbərlər
  - sitemap-categories.xml -> kateqoriyalar
  - news-sitemap.xml -> son 2 günün xəbərləri (Google News formatı)
"""
import re
import time
import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Set, Tuple
import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://report.az"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'az,en;q=0.5',
}


def fetch_url(url: str, timeout: int = 30, session: requests.Session = None) -> Tuple[int, str]:
    """Fetch a URL and return (status_code, content)"""
    try:
        if session:
            resp = session.get(url, timeout=timeout, allow_redirects=True)
        else:
            resp = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        return resp.status_code, resp.text
    except Exception as e:
        logger.warning(f"Failed to fetch {url}: {e}")
        return 0, ""


def clean_xml_namespaces(content: str) -> str:
    """Remove XML namespaces for simpler parsing"""
    content = re.sub(r' xmlns(?::[a-zA-Z]+)?="[^"]*"', '', content)
    return content


def parse_sitemap_for_article_urls(content: str) -> Tuple[List[str], List[str]]:
    """
    Parse sitemap XML content.
    Returns (article_urls, nested_sitemap_urls)
    """
    article_urls = []
    nested_sitemaps = []
    
    try:
        content_clean = clean_xml_namespaces(content)
        root = ET.fromstring(content_clean)
        
        # Sitemap index - contains nested sitemaps
        if 'sitemapindex' in root.tag.lower() or root.tag == 'sitemapindex':
            for sitemap in root.findall('.//sitemap'):
                loc = sitemap.find('loc')
                if loc is not None and loc.text:
                    nested_sitemaps.append(loc.text.strip())
        
        # Regular sitemap - contains URLs
        else:
            for url_elem in root.findall('.//url'):
                loc = url_elem.find('loc')
                if loc is not None and loc.text:
                    url = loc.text.strip()
                    nested_sitemaps.append(url) if 'sitemap' in url.lower() and url.endswith('.xml') else article_urls.append(url)
    
    except ET.ParseError:
        # Fallback: regex extraction
        for match in re.finditer(r'<loc>([^<]+)</loc>', content):
            url = match.group(1).strip()
            if url.startswith('http'):
                if 'sitemap' in url.lower() and url.endswith('.xml'):
                    nested_sitemaps.append(url)
                else:
                    article_urls.append(url)
    
    return article_urls, nested_sitemaps


def get_all_archive_sitemap_urls(session: requests.Session = None) -> List[str]:
    """
    Get all archive sitemap URLs from the sitemap index.
    Returns list of all sitemap URLs (including nested ones).
    """
    if session is None:
        session = requests.Session()
        session.headers.update(HEADERS)
    
    # Fetch the main sitemap index
    status, content = fetch_url(f"{BASE_URL}/sitemap.xml", session=session)
    if status != 200 or not content:
        logger.error("Could not fetch main sitemap.xml")
        return []
    
    _, sitemap_urls = parse_sitemap_for_article_urls(content)
    
    logger.info(f"Found {len(sitemap_urls)} sitemaps in index")
    return sitemap_urls


def get_all_sitemap_urls(session: requests.Session = None) -> Tuple[Set[str], List[str]]:
    """
    Crawl ALL sitemaps and return (article_urls_set, sitemap_sources).
    Handles the full archive from 2014 to present.
    """
    if session is None:
        session = requests.Session()
        session.headers.update(HEADERS)
    
    all_article_urls: Set[str] = set()
    sitemap_sources: List[str] = []
    visited_sitemaps: Set[str] = set()
    
    logger.info("Starting sitemap discovery...")
    
    # First check robots.txt for sitemap references
    status, robots_content = fetch_url(f"{BASE_URL}/robots.txt", session=session)
    robots_sitemaps = []
    if status == 200 and robots_content:
        for line in robots_content.splitlines():
            line = line.strip()
            if line.lower().startswith('sitemap:'):
                sm_url = line[8:].strip()
                if sm_url:
                    robots_sitemaps.append(sm_url)
        logger.info(f"robots.txt: {len(robots_sitemaps)} sitemap refs: {robots_sitemaps}")
    
    # Start with sitemap index
    sitemap_queue = list(set(robots_sitemaps + [
        f"{BASE_URL}/sitemap.xml",
        f"{BASE_URL}/news-sitemap.xml",
    ]))
    
    total_processed = 0
    
    while sitemap_queue:
        sitemap_url = sitemap_queue.pop(0)
        
        if sitemap_url in visited_sitemaps:
            continue
        visited_sitemaps.add(sitemap_url)
        
        logger.info(f"[{total_processed+1}] Processing: {sitemap_url}")
        time.sleep(0.3)  # Polite delay
        
        status, content = fetch_url(sitemap_url, session=session)
        if status != 200 or not content:
            logger.warning(f"  Could not fetch (status {status})")
            continue
        
        sitemap_sources.append(sitemap_url)
        total_processed += 1
        
        article_urls, nested = parse_sitemap_for_article_urls(content)
        
        before = len(all_article_urls)
        all_article_urls.update(article_urls)
        new_count = len(all_article_urls) - before
        
        logger.info(f"  -> {len(article_urls)} article URLs ({new_count} new), {len(nested)} nested sitemaps")
        
        # Add unvisited nested sitemaps to queue
        for nested_url in nested:
            if nested_url not in visited_sitemaps:
                sitemap_queue.append(nested_url)
    
    logger.info(f"\nSitemap discovery complete:")
    logger.info(f"  Total sitemaps processed: {total_processed}")
    logger.info(f"  Total article URLs found: {len(all_article_urls)}")
    
    return all_article_urls, sitemap_sources
