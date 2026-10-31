"""
run_discover.py - Saytdaki butun URL-leri tapir
Standalone script, terminal encoding problemini hess edir
"""
import sys
import os

# UTF-8 encoding
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

os.chdir(os.path.dirname(os.path.abspath(__file__)))

import logging
import time
from datetime import datetime
from pathlib import Path

# Setup logging to file (UTF-8)
Path("output/logs").mkdir(parents=True, exist_ok=True)
log_file = f"output/logs/discover_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)

print("=" * 60)
print("REPORT.AZ SCRAPER - DISCOVER MODE")
print("Sitemap vasitesile butun URL-ler tapilir...")
print("=" * 60)

from database import init_database, get_stats, add_discovered_urls
from sitemap_parser import get_all_sitemap_urls
from models import DiscoveredUrl

# Initialize DB
logger.info("Verilənlər bazası yaradılır...")
init_database()
logger.info("DB hazır.")

# Discover from sitemaps
logger.info("\nSitemap kəşfi başlayır...")
import requests

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'az,en;q=0.5',
})

t_start = time.time()
article_urls, sitemap_sources = get_all_sitemap_urls(session)

logger.info(f"\nSitemap kəşfi tamamlandı:")
logger.info(f"  Sitemap sayı: {len(sitemap_sources)}")
logger.info(f"  URL sayı: {len(article_urls)}")
logger.info(f"  Müddət: {time.time()-t_start:.1f}s")

# Save to DB
logger.info("\nURL-lər bazaya yazılır...")
discovered_list = []
for url in article_urls:
    discovered_list.append(DiscoveredUrl(
        url=url,
        source='sitemap',
        discovered_at=datetime.now(),
        priority=10
    ))

added = add_discovered_urls(discovered_list)
logger.info(f"Bazaya əlavə edildi: {added} yeni URL")

# Stats
stats = get_stats()
print("\n" + "=" * 60)
print("NƏTİCƏ:")
print(f"  Sitemaplardan tapılan URL: {len(article_urls):,}")
print(f"  Bazada yeni URL: {added:,}")
print(f"  DB-də cəmi URL: {stats.get('total_discovered', 0):,}")
print(f"  Log faylı: {log_file}")
print("=" * 60)

