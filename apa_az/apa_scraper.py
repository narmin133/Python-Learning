"""
apa_scraper.py - https://apa.az/ saytının xəbərlərini toplayan sadə və anlaşıqlı skript
"""
import sys
import os
import csv
import requests
from bs4 import BeautifulSoup
from datetime import datetime

os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
os.chdir(os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("APA.AZ SAYTINDAN CANLI XƏBƏRLƏRİN TOPLANMASI")
print("=" * 60)

# 1. ADDIM: Brauzer kimi maskalanırıq (User-Agent)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'az,en;q=0.5',
}

session = requests.Session()
session.headers.update(HEADERS)

# 2. ADDIM: APA.az-ın ana səhifəsinə girib ən son xəbər linklərini tapırıq
print("\n1. Ana səhifədən ən son xəbər linkləri toplanır...")
main_page = session.get("https://apa.az/", timeout=15)
main_page.encoding = 'utf-8'

soup_main = BeautifulSoup(main_page.text, 'lxml')

news_urls = []
for a in soup_main.find_all('a', href=True):
    href = a['href']
    # APA.az xəbər linklərinin sonunda rəqəm olur: məsələn /semkirde-...-1009847
    if href.startswith('https://apa.az/') and any(char.isdigit() for char in href.split('-')[-1]):
        if href not in news_urls and 'locale=' not in href:
            news_urls.append(href)

print(f"✅ Tapılan xəbər sayı: {len(news_urls)}")

# 3. ADDIM: Hər xəbəri açıb içindən Başlıq, Mətn, Tarix və Kateqoriyanı götürürük
results = []
limit = 15  # Nümunə üçün ilk 15 xəbəri dərhal çəkirik

print(f"\n2. Xəbərlər oxunur (İlk {limit} xəbər)...")

for i, url in enumerate(news_urls[:limit], 1):
    try:
        r = session.get(url, timeout=10)
        r.encoding = 'utf-8' # Bələdçimizdəki qızıl qayda: Azərbaycan hərfləri xarab olmasın!
        
        soup = BeautifulSoup(r.text, 'lxml')
        
        # Başlıq (h2 və ya og:title)
        h2 = soup.find('h2')
        og_title = soup.find('meta', property='og:title')
        title = h2.get_text().strip() if h2 else (og_title.get('content') if og_title else "Başlıq tapılmadı")
        
        # Kateqoriya (h1)
        h1 = soup.find('h1')
        category = h1.get_text().strip() if h1 else "Ümumi"
        
        # Tarix (class="date")
        date_elem = soup.find(class_='date')
        date_text = date_elem.get_text().strip() if date_elem else ""
        
        # Mətn (div.texts içindəki paraqraflar)
        texts_div = soup.find('div', class_='texts')
        if texts_div:
            # Lazımsız teqləri təmizləyirik
            for tag in texts_div.find_all(['script', 'style', 'iframe']):
                tag.decompose()
            paragraphs = [p.get_text().strip() for p in texts_div.find_all('p') if p.get_text().strip()]
            content = "\n\n".join(paragraphs)
        else:
            content = ""
            
        # Şəkil linki
        og_img = soup.find('meta', property='og:image')
        image_url = og_img.get('content') if og_img else ""
        
        results.append({
            'url': url,
            'title': title,
            'category': category,
            'published_at': date_text,
            'image_url': image_url,
            'content': content
        })
        
        print(f"  [{i}/{limit}] ✓ {title[:60]}... ({category})")
        
    except Exception as e:
        print(f"  [{i}/{limit}] ✗ Xəta: {e}")

# 4. ADDIM: Nəticələri birbaşa Excel üçün CSV faylına yazırıq (utf-8-sig ilə)
csv_filename = "apa_articles.csv"
print(f"\n3. Məlumatlar '{csv_filename}' faylına yazılır...")

fields = ['title', 'category', 'published_at', 'url', 'image_url', 'content']

with open(csv_filename, 'w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(results)

print("\n" + "=" * 60)
print(f"TAMAMLANDI! '{csv_filename}' faylı yaradıldı.")
print("=" * 60)

