"""
article_parser.py - Parse individual article pages from report.az
HTML structure (discovered through analysis):
  - Title: div.news-detail__item h1, or <h1>
  - Content: div.news-detail__desc
  - Author: div.news-detail__authors
  - Date: div.date (contains date and time)
  - Category: div.news-detail__head (first link)
"""
import re
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup, Tag

from models import Article, MediaItem

logger = logging.getLogger(__name__)
BASE_URL = "https://report.az"


def clean_text(text: str) -> str:
    """Clean and normalize text"""
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def parse_date(date_str: str) -> Optional[datetime]:
    """Parse various date formats used by report.az"""
    if not date_str:
        return None
    
    date_str = date_str.strip()
    
    # Common formats to try
    formats = [
        "%Y-%m-%dT%H:%M:%S%z",      # ISO 8601 with timezone
        "%Y-%m-%dT%H:%M:%S.%f%z",   # ISO 8601 with microseconds
        "%Y-%m-%dT%H:%M:%S+00:00",  # ISO with explicit UTC
        "%Y-%m-%dT%H:%M:%S",        # ISO without timezone
        "%Y-%m-%d %H:%M:%S",        # Standard datetime
        "%Y-%m-%d %H:%M",           # Without seconds
        "%d.%m.%Y %H:%M:%S",        # Azerbaijani format with seconds
        "%d.%m.%Y %H:%M",           # Azerbaijani format
        "%d %B, %Y",                # e.g. "30 October, 2026"
        "%d %B %Y",                 # e.g. "30 October 2026"
        "%B %d, %Y",                # e.g. "October 30, 2026"
        "%Y-%m-%d",                 # Date only
        "%d.%m.%Y",                 # Azerbaijani date only
    ]
    
    # Month name mapping (English and Azerbaijani)
    month_map_en = {
        'january': '01', 'february': '02', 'march': '03', 'april': '04',
        'may': '05', 'june': '06', 'july': '07', 'august': '08',
        'september': '09', 'october': '10', 'november': '11', 'december': '12'
    }
    month_map_az = {
        'yanvar': '01', 'fevral': '02', 'mart': '03', 'aprel': '04',
        'may': '05', 'iyun': '06', 'iyul': '07', 'avqust': '08',
        'sentyabr': '09', 'oktyabr': '10', 'noyabr': '11', 'dekabr': '12'
    }
    month_map_ru = {
        'января': '01', 'февраля': '02', 'марта': '03', 'апреля': '04',
        'мая': '05', 'июня': '06', 'июля': '07', 'августа': '08',
        'сентября': '09', 'октября': '10', 'ноября': '11', 'декабря': '12'
    }
    
    # Try direct parsing
    for fmt in formats:
        try:
            # Handle timezone offset format
            date_to_parse = date_str
            if '+' in date_str[10:] or date_str.endswith('Z'):
                date_to_parse = re.sub(r'\+\d{2}:\d{2}$', '', date_str).rstrip('Z')
            return datetime.strptime(date_to_parse, fmt.replace('%z', ''))
        except ValueError:
            pass
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    # Handle month names
    date_lower = date_str.lower()
    for month_map in [month_map_en, month_map_az, month_map_ru]:
        for month_name, month_num in month_map.items():
            if month_name in date_lower:
                modified = date_lower.replace(month_name, month_num)
                # Try to extract day, month, year, time
                patterns = [
                    r'(\d{1,2})\s*[, ]\s*(\d{2})\s*[, ]\s*(\d{4})(?:[, ]\s*(\d{2}):(\d{2}))?',
                    r'(\d{4})[^\d](\d{2})[^\d](\d{1,2})(?:[^\d](\d{2}):(\d{2}))?',
                ]
                # Simple pattern: "30 10, 2026 15:10"
                match = re.search(r'(\d{1,2})\s+(\d{2})[,\s]+(\d{4})(?:[\s,]+(\d{2}):(\d{2}))?', modified)
                if match:
                    try:
                        day, month, year = match.group(1), match.group(2), match.group(3)
                        hour = match.group(4) or '00'
                        minute = match.group(5) or '00'
                        return datetime(int(year), int(month), int(day), int(hour), int(minute))
                    except (ValueError, TypeError):
                        pass
    
    # Try regex extraction for common patterns
    patterns = [
        r'(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}(?::\d{2})?)',
        r'(\d{2}\.\d{2}\.\d{4})[T ](\d{2}:\d{2}(?::\d{2})?)',
        r'(\d{4}-\d{2}-\d{2})',
        r'(\d{2}\.\d{2}\.\d{4})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, date_str)
        if match:
            try:
                if len(match.groups()) == 2:
                    date_part = match.group(1)
                    time_part = match.group(2)
                    combined = f"{date_part} {time_part}"
                else:
                    combined = match.group(1)
                
                for fmt in formats:
                    try:
                        return datetime.strptime(combined, fmt)
                    except ValueError:
                        continue
            except Exception:
                pass
    
    logger.debug(f"Could not parse date: {date_str!r}")
    return None


def extract_json_ld(soup: BeautifulSoup) -> Optional[Dict]:
    """Extract JSON-LD structured data"""
    best = None
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(script.string or '')
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and item.get('@type') in ('NewsArticle', 'Article', 'BlogPosting', 'ReportageNewsArticle'):
                        return item
                if data:
                    best = data[0] if best is None else best
            elif isinstance(data, dict):
                if data.get('@type') in ('NewsArticle', 'Article', 'BlogPosting', 'ReportageNewsArticle'):
                    return data
                if best is None:
                    best = data
        except (json.JSONDecodeError, TypeError):
            continue
    return best


def extract_og_data(soup: BeautifulSoup) -> Dict[str, Optional[str]]:
    """Extract Open Graph metadata"""
    og = {}
    for meta in soup.find_all('meta', property=re.compile(r'^og:')):
        prop = meta.get('property', '').replace('og:', '')
        content = meta.get('content', '')
        if prop and content:
            og[prop] = content
    return og


def extract_article_content_reportaz(soup: BeautifulSoup) -> Tuple[str, bool]:
    """
    Extract article content from report.az specific structure.
    Main content is in div.news-detail__desc
    Returns (content_text, is_incomplete)
    """
    content_text = ""
    is_incomplete = False
    
    # Primary selector for report.az
    content_selectors = [
        ('div', {'class': 'news-detail__desc'}),
        ('div', {'class': re.compile(r'news-detail', re.I)}),
        ('div', {'class': re.compile(r'article.*body|article.*content|article.*text|post.*content|entry.*content', re.I)}),
        ('div', {'itemprop': 'articleBody'}),
        ('article', {}),
        ('div', {'class': 'article'}),
        ('main', {}),
    ]
    
    for tag, attrs in content_selectors:
        container = soup.find(tag, attrs)
        if container:
            # Remove unwanted child elements
            for unwanted in container.find_all(['script', 'style', 'noscript', 'iframe']):
                unwanted.decompose()
            for unwanted in container.find_all(class_=re.compile(r'share|social|comment|advert|banner|related', re.I)):
                unwanted.decompose()
            
            # Extract paragraphs maintaining structure
            paragraphs = []
            for elem in container.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'blockquote', 'span']):
                text = clean_text(elem.get_text())
                if text and len(text) > 10:
                    paragraphs.append(text)
            
            if paragraphs:
                content_text = '\n\n'.join(paragraphs)
                break
            
            # Fallback to full text of container
            text = clean_text(container.get_text())
            if text and len(text) > 50:
                content_text = text
                break
    
    if len(content_text) < 50:
        is_incomplete = True
        # Try broader search
        body = soup.find('body')
        if body:
            for unwanted in body.find_all(['header', 'footer', 'nav', 'script', 'style']):
                unwanted.decompose()
            text = clean_text(body.get_text())
            if text and len(text) > len(content_text):
                content_text = text[:10000]
    
    return content_text, is_incomplete


def extract_images_reportaz(soup: BeautifulSoup, base_url: str = BASE_URL) -> List[MediaItem]:
    """Extract images from report.az articles"""
    images = []
    seen_urls = set()
    position = 0
    
    # First get OG image (main image)
    og_img = soup.find('meta', property='og:image')
    if og_img and og_img.get('content'):
        url = og_img['content'].strip()
        if url not in seen_urls:
            seen_urls.add(url)
            images.append(MediaItem(
                media_type='image',
                url=url,
                is_main=True,
                position=position
            ))
            position += 1
    
    # Content area images
    for selector in ['div.news-detail__desc', 'div.news-detail__item', 'article', 'main']:
        parts = selector.split('.')
        if len(parts) == 2:
            container = soup.find(parts[0], class_=parts[1])
        else:
            container = soup.find(selector)
        
        if container:
            for img in container.find_all('img'):
                src = (img.get('src') or img.get('data-src') or 
                       img.get('data-lazy-src') or img.get('data-original', ''))
                if not src:
                    continue
                
                if src.startswith('//'):
                    src = 'https:' + src
                elif not src.startswith('http'):
                    src = urljoin(base_url, src)
                
                src = src.split('?')[0]  # Remove query strings
                
                # Skip tiny images
                w = img.get('width', '0')
                h = img.get('height', '0')
                try:
                    if int(str(w)) < 50 or int(str(h)) < 50:
                        continue
                except (ValueError, TypeError):
                    pass
                
                if src in seen_urls:
                    continue
                seen_urls.add(src)
                
                alt = clean_text(img.get('alt', ''))
                caption_tag = img.find_next_sibling('figcaption')
                if not caption_tag:
                    fig = img.find_parent('figure')
                    if fig:
                        caption_tag = fig.find('figcaption')
                caption = clean_text(caption_tag.get_text()) if caption_tag else None
                
                images.append(MediaItem(
                    media_type='image',
                    url=src,
                    alt_text=alt or None,
                    caption=caption,
                    is_main=False,
                    position=position
                ))
                position += 1
            break
    
    return images


def extract_videos_reportaz(soup: BeautifulSoup, base_url: str = BASE_URL) -> List[MediaItem]:
    """Extract videos from report.az articles"""
    videos = []
    seen_urls = set()
    position = 0
    
    for iframe in soup.find_all('iframe'):
        src = iframe.get('src', '')
        if not src:
            continue
        
        if any(d in src for d in ['youtube.com', 'youtu.be', 'vimeo.com', 'dailymotion.com', 'brightcove']):
            if src in seen_urls:
                continue
            seen_urls.add(src)
            videos.append(MediaItem(
                media_type='video',
                url=src,
                title=clean_text(iframe.get('title', '')) or None,
                position=position
            ))
            position += 1
    
    for video in soup.find_all('video'):
        src = video.get('src', '')
        if not src:
            source = video.find('source')
            if source:
                src = source.get('src', '')
        
        if src:
            if not src.startswith('http'):
                src = urljoin(base_url, src)
            if src not in seen_urls:
                seen_urls.add(src)
                videos.append(MediaItem(
                    media_type='video',
                    url=src,
                    position=position
                ))
                position += 1
    
    return videos


def extract_tags_reportaz(soup: BeautifulSoup) -> List[str]:
    """Extract tags from report.az articles"""
    tags = []
    seen = set()
    
    tag_selectors = [
        ('div', {'class': re.compile(r'tags?|teqs?|keywords?', re.I)}),
        ('ul', {'class': re.compile(r'tags?|teqs?', re.I)}),
        ('section', {'class': re.compile(r'tags?|teqs?', re.I)}),
        ('div', {'class': 'post-tags'}),
        ('div', {'class': 'article-tags'}),
        ('div', {'class': 'news-tags'}),
    ]
    
    for tag_name, attrs in tag_selectors:
        container = soup.find(tag_name, attrs)
        if container:
            for link in container.find_all('a'):
                tag_text = clean_text(link.get_text())
                if tag_text and tag_text not in seen and len(tag_text) < 100:
                    tags.append(tag_text)
                    seen.add(tag_text)
    
    # JSON-LD keywords
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(script.string or '')
            if isinstance(data, dict):
                kws = data.get('keywords', [])
                if isinstance(kws, list):
                    for kw in kws:
                        kw = clean_text(str(kw))
                        if kw and kw not in seen:
                            tags.append(kw)
                            seen.add(kw)
                elif isinstance(kws, str):
                    for kw in kws.split(','):
                        kw = clean_text(kw)
                        if kw and kw not in seen:
                            tags.append(kw)
                            seen.add(kw)
        except Exception:
            pass
    
    return tags


def extract_related_articles(soup: BeautifulSoup, base_url: str = BASE_URL) -> List[str]:
    """Extract related article URLs"""
    related = []
    seen = set()
    
    selectors = [
        ('div', {'class': re.compile(r'related|oxsar|similar|son-xeberler', re.I)}),
        ('section', {'class': re.compile(r'related|oxsar', re.I)}),
        ('div', {'class': 'last-news'}),
        ('div', {'id': re.compile(r'related', re.I)}),
    ]
    
    for tag_name, attrs in selectors:
        container = soup.find(tag_name, attrs)
        if container:
            for link in container.find_all('a', href=True):
                href = link['href']
                if not href.startswith('http'):
                    href = urljoin(base_url, href)
                if 'report.az' in href and href not in seen and href != base_url:
                    related.append(href)
                    seen.add(href)
    
    return related[:20]  # Limit to 20


def parse_article(url: str, html_content: str) -> Article:
    """
    Parse a report.az article page and extract all available data.
    """
    article = Article(url=url, scraped_at=datetime.now())
    
    try:
        soup = BeautifulSoup(html_content, 'lxml')
        
        # ---- JSON-LD structured data ----
        json_ld = extract_json_ld(soup)
        if json_ld:
            article.json_ld = json.dumps(json_ld, ensure_ascii=False)
            
            if isinstance(json_ld, dict):
                # Title from JSON-LD
                article.title = json_ld.get('headline') or json_ld.get('name')
                
                # Summary
                article.summary = json_ld.get('description')
                
                # Author
                author_data = json_ld.get('author')
                if author_data:
                    if isinstance(author_data, dict):
                        article.author = author_data.get('name')
                    elif isinstance(author_data, list) and author_data:
                        first = author_data[0]
                        article.author = first.get('name') if isinstance(first, dict) else str(first)
                    elif isinstance(author_data, str):
                        article.author = author_data
                
                # Publisher/source
                publisher = json_ld.get('publisher', {})
                if isinstance(publisher, dict):
                    article.source = publisher.get('name', 'Report.az')
                
                # Published date
                pub_raw = json_ld.get('datePublished') or json_ld.get('dateCreated')
                if pub_raw:
                    article.published_at_raw = pub_raw
                    article.published_at = parse_date(pub_raw)
                
                # Updated date
                upd_raw = json_ld.get('dateModified')
                if upd_raw:
                    article.updated_at_raw = upd_raw
                    article.updated_at = parse_date(upd_raw)
                
                # Canonical URL
                main_url = json_ld.get('url') or json_ld.get('mainEntityOfPage', {})
                if isinstance(main_url, dict):
                    main_url = main_url.get('@id') or main_url.get('url')
                if main_url and isinstance(main_url, str):
                    article.canonical_url = main_url
                
                # Article section (category)
                section = json_ld.get('articleSection')
                if section:
                    if isinstance(section, list):
                        section = section[0] if section else None
                    if isinstance(section, str):
                        article.category = section
                
                # Keywords
                kws = json_ld.get('keywords')
                if kws:
                    if isinstance(kws, list):
                        article.meta_keywords = ', '.join(str(k) for k in kws)
                    elif isinstance(kws, str):
                        article.meta_keywords = kws
                
                # Main image from JSON-LD
                img_data = json_ld.get('image')
                if img_data:
                    if isinstance(img_data, str):
                        article.main_image_url = img_data
                    elif isinstance(img_data, dict):
                        article.main_image_url = img_data.get('url') or img_data.get('@id')
                    elif isinstance(img_data, list) and img_data:
                        first = img_data[0]
                        if isinstance(first, str):
                            article.main_image_url = first
                        elif isinstance(first, dict):
                            article.main_image_url = first.get('url')
        
        # ---- Open Graph metadata ----
        og = extract_og_data(soup)
        article.og_title = og.get('title')
        article.og_description = og.get('description')
        article.og_image = og.get('image')
        
        if not article.title:
            article.title = article.og_title
        if not article.summary:
            article.summary = article.og_description
        if not article.main_image_url:
            article.main_image_url = article.og_image
        
        # ---- Canonical URL ----
        canonical_tag = soup.find('link', rel='canonical')
        if canonical_tag and not article.canonical_url:
            article.canonical_url = canonical_tag.get('href')
        
        # ---- HTML Title ----
        if not article.title:
            title_tag = soup.find('title')
            if title_tag:
                title_text = clean_text(title_tag.get_text())
                for sep in [' | Report.az', ' - Report.az', ' | report.az', ' - report.az', ' — Report']:
                    if sep in title_text:
                        title_text = title_text.split(sep)[0].strip()
                        break
                article.title = title_text
        
        # H1 tag (most accurate for article title)
        h1 = soup.find('h1')
        if h1:
            h1_text = clean_text(h1.get_text())
            if h1_text and len(h1_text) > 5:
                article.title = h1_text
        
        # ---- Meta description ----
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            article.meta_description = meta_desc.get('content')
            if not article.summary:
                article.summary = article.meta_description
        
        # ---- Language ----
        html_tag = soup.find('html')
        if html_tag:
            article.language = html_tag.get('lang', 'az')
        
        # Determine from URL
        url_path = urlparse(url).path
        if url_path.startswith('/en/') or url_path.startswith('/en-'):
            article.language = 'en'
        elif url_path.startswith('/ru/') or url_path.startswith('/ru-'):
            article.language = 'ru'
        
        # ---- Category from report.az structure ----
        # Category is in div.news-detail__head
        cat_container = soup.find('div', class_='news-detail__head')
        if cat_container:
            links = cat_container.find_all('a')
            if links:
                article.category = clean_text(links[0].get_text())
                article.category_url = urljoin(BASE_URL, links[0].get('href', ''))
            if len(links) >= 2:
                article.subcategory = clean_text(links[1].get_text())
                article.subcategory_url = urljoin(BASE_URL, links[1].get('href', ''))
        
        # Fallback: breadcrumbs
        if not article.category:
            for bc_tag, bc_attrs in [
                ('nav', {'aria-label': re.compile(r'breadcrumb', re.I)}),
                ('div', {'class': re.compile(r'breadcrumb', re.I)}),
                ('ol', {'class': re.compile(r'breadcrumb', re.I)}),
            ]:
                bc = soup.find(bc_tag, bc_attrs)
                if bc:
                    links = bc.find_all('a')
                    if len(links) >= 2:
                        article.category = clean_text(links[1].get_text())
                        article.category_url = urljoin(BASE_URL, links[1].get('href', ''))
                    if len(links) >= 3:
                        article.subcategory = clean_text(links[2].get_text())
                        article.subcategory_url = urljoin(BASE_URL, links[2].get('href', ''))
                    break
        
        # Try to derive category from URL path
        if not article.category:
            parts = [p for p in url_path.split('/') if p]
            if len(parts) >= 2:
                article.category = parts[0].replace('-', ' ').title()
        
        # ---- Author ----
        if not article.author:
            author_container = soup.find('div', class_='news-detail__authors')
            if author_container:
                # Skip "Author" label, get the actual name
                author_links = author_container.find_all('a')
                if author_links:
                    article.author = clean_text(author_links[-1].get_text())
                else:
                    # Get text, remove "Author" prefix
                    author_text = clean_text(author_container.get_text())
                    author_text = re.sub(r'^Author[:\s]*', '', author_text, flags=re.I).strip()
                    if author_text and len(author_text) < 100:
                        article.author = author_text
            
            if not article.author:
                for tag_name, attrs in [
                    ('span', {'class': re.compile(r'author|muellif', re.I)}),
                    ('div', {'class': re.compile(r'author', re.I)}),
                    ('a', {'rel': 'author'}),
                    ('span', {'itemprop': 'author'}),
                ]:
                    elem = soup.find(tag_name, attrs)
                    if elem:
                        text = clean_text(elem.get_text())
                        if text and len(text) < 100:
                            article.author = text
                            break
        
        article.journalist = article.author
        
        # ---- Published date ----
        if not article.published_at:
            # report.az uses div.date class for dates
            date_elem = soup.find(class_='date')
            if date_elem:
                date_text = clean_text(date_elem.get_text())
                # Format is typically "30 October, 2026 \n15:10" or similar
                # Combine all text
                if date_text:
                    article.published_at_raw = date_text
                    article.published_at = parse_date(date_text)
            
            # Try time tags
            if not article.published_at:
                for time_tag in soup.find_all('time'):
                    dt_attr = time_tag.get('datetime') or time_tag.get('content')
                    raw = dt_attr or clean_text(time_tag.get_text())
                    if raw:
                        parsed = parse_date(raw)
                        if parsed:
                            article.published_at = parsed
                            article.published_at_raw = raw
                            break
            
            # Meta tags for date
            if not article.published_at:
                for meta_name, meta_attr in [
                    ({'property': 'article:published_time'}, 'content'),
                    ({'name': 'publish_date'}, 'content'),
                    ({'itemprop': 'datePublished'}, 'content'),
                    ({'name': 'date'}, 'content'),
                ]:
                    meta = soup.find('meta', attrs=meta_name)
                    if meta:
                        raw = meta.get(meta_attr, '')
                        if raw:
                            parsed = parse_date(raw)
                            if parsed:
                                article.published_at = parsed
                                article.published_at_raw = raw
                                break
        
        # ---- Updated date ----
        if not article.updated_at:
            for meta_name, meta_attr in [
                ({'property': 'article:modified_time'}, 'content'),
                ({'itemprop': 'dateModified'}, 'content'),
            ]:
                meta = soup.find('meta', attrs=meta_name)
                if meta:
                    raw = meta.get(meta_attr, '')
                    if raw:
                        parsed = parse_date(raw)
                        if parsed:
                            article.updated_at = parsed
                            article.updated_at_raw = raw
                            break
        
        # ---- Article content ----
        content_text, is_incomplete = extract_article_content_reportaz(soup)
        article.content = content_text
        article.content_length = len(content_text)
        article.is_incomplete = is_incomplete
        
        # ---- Media ----
        images = extract_images_reportaz(soup)
        article.images = [img.url for img in images]
        if images and not article.main_image_url:
            article.main_image_url = images[0].url
        
        videos = extract_videos_reportaz(soup)
        article.videos = [vid.url for vid in videos]
        
        # ---- Tags ----
        article.tags = extract_tags_reportaz(soup)
        
        # ---- Related articles ----
        article.related_articles = extract_related_articles(soup)
        
        # ---- Set status ----
        if article.title and len(article.title) > 3:
            article.status = 'success'
        else:
            article.status = 'failed'
            article.error_message = 'No title found - possibly blocked or not an article page'
    
    except Exception as e:
        logger.error(f"Error parsing article {url}: {e}", exc_info=True)
        article.status = 'failed'
        article.error_message = str(e)[:500]
    
    return article
