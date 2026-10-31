"""
fix_and_refresh_az.py - Report.az-ın Azərbaycan dilli xəbərlərini toplayır və UTF-8 ilə ixrac edir
"""
import sys
import os
import re
import csv
import logging
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from database import init_database, get_connection, save_article, update_url_status
from article_parser import parse_article
from discovery import HEADERS, normalize_url, is_article_url
from fast_scraper import save_article_data
from exporter import export_all, get_all_articles_ordered, article_to_export_dict, OUTPUT_DIR

print("=" * 60)
print("REPORT.AZ - AZƏRBAYCAN DİLLİ XƏBƏRLƏRİN TOPLANMASI (UTF-8)")
print("=" * 60)

init_database()
session = requests.Session()
session.headers.update(HEADERS)

# 1. Canlı sitemap və səhifələrdən AZƏRBAYCAN dilli xəbər URL-lərini toplayaq
r = session.get("https://report.az/news-sitemap.xml", timeout=20)
urls = re.findall(r'<loc>([^<]+)</loc>', r.text)

az_urls = []
for u in urls:
    u = u.strip()
    if 'report.az' in u and '/ru/' not in u and '/en/' not in u and is_article_url(u):
        az_urls.append(normalize_url(u))

for page_url in ["https://report.az/", "https://report.az/son-xeberler/"]:
    try:
        r_page = session.get(page_url, timeout=15)
        r_page.encoding = 'utf-8'
        soup = BeautifulSoup(r_page.text, 'lxml')
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.startswith('/'):
                href = 'https://report.az' + href
            if 'report.az' in href and '/ru/' not in href and '/en/' not in href and is_article_url(href):
                az_urls.append(normalize_url(href))
    except Exception as e:
        pass

az_urls = list(dict.fromkeys(az_urls))
print(f"📡 Tapılan unikal Azərbaycan dilli xəbər URL sayı: {len(az_urls)}")

# 2. Çoxaxınlı rejimdə ilk 80 yeni Azərbaycan xəbərini yükləyək
TARGET_COUNT = 80
urls_to_scrape = az_urls[:TARGET_COUNT]
print(f"⚡ Toplanacaq xəbər sayı: {len(urls_to_scrape)}")

def fetch_and_save(url):
    try:
        resp = session.get(url, timeout=15)
        if resp.status_code == 200:
            resp.encoding = 'utf-8' # TƏMİZ UTF-8 KODLAŞDIRMASI
            article = parse_article(url, resp.text)
            article.language = 'az'
            if article.title:
                save_article_data(article)
                update_url_status(url, 'scraped')
                return True, article.title
        return False, f"HTTP {resp.status_code}"
    except Exception as e:
        return False, str(e)

success_count = 0
with ThreadPoolExecutor(max_workers=6) as executor:
    futures = {executor.submit(fetch_and_save, url): url for url in urls_to_scrape}
    for f in as_completed(futures):
        ok, title = f.result()
        if ok:
            success_count += 1
            if success_count % 10 == 0:
                print(f"  [{success_count}/{len(urls_to_scrape)}] ✓ {title[:60]}...")

print(f"\n✅ Uğurla toplanmış yeni Azərbaycan dilli xəbərlər: {success_count}")

# 3. İxrac: həm əsas articles.csv, həm də yalnız Azərbaycan dilində articles_az.csv
print("\n📂 Fayllar UTF-8 formatında ixrac edilir...")

# Bütün xəbərlər (AZ xəbərləri ən başda olmaqla)
all_articles = get_all_articles_ordered(order='desc')

# Sıralama: əvvəlcə azərbaycanca olanlar, sonra dərc tarixinə görə
all_articles.sort(key=lambda x: (1 if x.get('language') == 'az' else 0, x.get('published_at') or ''), reverse=True)

csv_fields = [
    'id', 'url', 'title', 'subtitle', 'summary',
    'author', 'journalist', 'source', 'category', 'subcategory',
    'language', 'published_at', 'published_at_raw', 'updated_at',
    'scraped_at', 'main_image_url', 'meta_description', 'meta_keywords',
    'og_title', 'content_length', 'is_incomplete', 'status'
]

# Əsas articles.csv-yə yazaq
with open(OUTPUT_DIR / "articles.csv", 'w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=csv_fields, extrasaction='ignore')
    writer.writeheader()
    for art in all_articles:
        writer.writerow({k: art.get(k, '') for k in csv_fields})

# Yalnız təmiz Azərbaycan dilində olan xəbərlər üçün articles_az.csv
az_only = [a for a in all_articles if a.get('language') == 'az']
with open(OUTPUT_DIR / "articles_az.csv", 'w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=csv_fields, extrasaction='ignore')
    writer.writeheader()
    for art in az_only:
        writer.writerow({k: art.get(k, '') for k in csv_fields})

# JSON və JSONL də yenilənsin
export_all(order='desc')

print(f"✅ articles.csv yeniləndi (Cəmi: {len(all_articles)} xəbər)")
print(f"✅ articles_az.csv yaradıldı (Yalnız Azərbaycan dilində: {len(az_only)} xəbər)")
