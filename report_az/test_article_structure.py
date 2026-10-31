"""
Test script to analyze report.az article structure
"""
import requests
from bs4 import BeautifulSoup
import json
import re

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'az,en;q=0.5',
}

session = requests.Session()
session.headers.update(HEADERS)

# Get a sample article URL from news-sitemap
r = session.get('https://report.az/news-sitemap.xml', timeout=20)
content = r.text

import xml.etree.ElementTree as ET
content_clean = re.sub(r' xmlns(?::[a-zA-Z0-9]+)?="[^"]*"', '', content)
content_clean = re.sub(r'<([a-zA-Z0-9]+):([a-zA-Z0-9]+)', r'<\1_\2', content_clean)
content_clean = re.sub(r'</([a-zA-Z0-9]+):([a-zA-Z0-9]+)', r'</\1_\2', content_clean)
try:
    root = ET.fromstring(content_clean)
except ET.ParseError as e:
    # Fallback to regex
    print(f"XML parse error: {e}")
    sample_urls = re.findall(r'<loc>([^<]+)</loc>', content)
    sample_urls = [u.strip() for u in sample_urls if 'report.az' in u][:3]
    root = None

if root is not None:
    sample_urls = []
    for url_elem in root.findall('.//url'):
        loc = url_elem.find('loc')
        if loc is not None and loc.text:
            sample_urls.append(loc.text.strip())
        if len(sample_urls) >= 3:
            break

print(f"Sample URLs from news-sitemap:")
for url in sample_urls:
    print(f"  {url}")

# Parse first article
if sample_urls:
    url = sample_urls[0]
    print(f"\n{'='*60}")
    print(f"Analyzing: {url}")
    print('='*60)
    
    r2 = session.get(url, timeout=20)
    soup = BeautifulSoup(r2.text, 'lxml')
    
    # Title
    h1 = soup.find('h1')
    print(f"\nH1: {h1.get_text().strip() if h1 else 'NOT FOUND'}")
    
    title_tag = soup.find('title')
    print(f"Title tag: {title_tag.get_text().strip() if title_tag else 'NOT FOUND'}")
    
    # Meta
    og_title = soup.find('meta', property='og:title')
    print(f"OG Title: {og_title.get('content', '') if og_title else 'NOT FOUND'}")
    
    # Dates
    print("\n--- Date elements ---")
    for time_tag in soup.find_all('time')[:5]:
        print(f"  <time>: {time_tag}")
    
    # Look for date-related classes
    for cls in ['date', 'tarix', 'time', 'publish', 'created', 'meta']:
        elems = soup.find_all(class_=re.compile(cls, re.I))
        if elems:
            print(f"  class={cls}: {elems[0].get_text().strip()[:100]}")
    
    # JSON-LD
    print("\n--- JSON-LD ---")
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(script.string or '')
            print(json.dumps(data, ensure_ascii=False, indent=2)[:500])
        except:
            pass
    
    # Article body classes
    print("\n--- Possible content containers ---")
    for div in soup.find_all('div', class_=True):
        cls_str = ' '.join(div.get('class', []))
        if any(kw in cls_str.lower() for kw in ['article', 'content', 'body', 'text', 'post', 'news']):
            text = div.get_text()[:100].strip()
            if len(text) > 50:
                print(f"  div.{cls_str}: {text[:80]}...")
    
    # All meta tags
    print("\n--- Key meta tags ---")
    for meta in soup.find_all('meta'):
        name = meta.get('name', '') or meta.get('property', '')
        if any(kw in name.lower() for kw in ['date', 'time', 'publish', 'author', 'article']):
            print(f"  {name}: {meta.get('content', '')}")
