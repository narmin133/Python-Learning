# ============================================================
# APA.AZ BÜTÜN XƏBƏRLƏRİN TOPLANMASI VƏ YENİDƏN KÖHNƏYƏ SIRALANMASI
# ============================================================

import sys
import os
import re
import time
import requests
from bs4 import BeautifulSoup
import csv
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# Terminalda Azərbaycan hərfləri xəta verməsin
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
os.chdir(os.path.dirname(os.path.abspath(__file__)))

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
}

print("=" * 60)
print("APA.AZ - XƏBƏRLƏRİN TOPLANMASI VƏ XRONOLOJİ SIRALANMASI")
print("=" * 60)

session = requests.Session()
session.headers.update(headers)

# Azərbaycan aylarını rəqəmə çevirən lüğət
AYLAR = {
    'yanvar': 1, 'fevral': 2, 'mart': 3, 'aprel': 4,
    'may': 5, 'iyun': 6, 'iyul': 7, 'avqust': 8,
    'sentyabr': 9, 'oktyabr': 10, 'noyabr': 11, 'dekabr': 12
}

def tarixi_standarta_cevir(tarix_metni, url):
    """
    Tarixi (məs: '31 oktyabr 2026 23:10') müqayisə edilə bilən obyektə çevirir.
    Əgər tarix oxunmazsa, linkin sonundakı xəbər ID-sini əsas götürür.
    """
    try:
        # Regex ilə gün, ay, il və saatı tapırıq
        # Nümunə: "31 oktyabr 2026 18:48"
        t_clean = tarix_metni.lower()
        match = re.search(r'(\d{1,2})\s+([a-zəöüğışç]+)\s+(\d{4})(?:\s+(\d{1,2}):(\d{2}))?', t_clean)
        if match:
            gun = int(match.group(1))
            ay_adi = match.group(2)
            il = int(match.group(3))
            saat = int(match.group(4)) if match.group(4) else 0
            deqiqe = int(match.group(5)) if match.group(5) else 0
            
            ay = AYLAR.get(ay_adi, 1)
            return datetime(il, ay, gun, saat, deqiqe)
    except:
        pass
    
    # Əgər tarix çıxmazsa, URL-in sonundakı xəbər ID nömrəsini götürürük
    id_match = re.search(r'-(\d{5,8})', url)
    xeber_id = int(id_match.group(1)) if id_match else 0
    return xeber_id

# 1. ADDIM: XƏBƏR LİNKLƏRİNİ TOPLAYIQ
print("\n1. Saytdan xəbər linkləri toplanır...")

tapilan_linkler = set()
menbeler = [
    "https://apa.az/",
    "https://apa.az/xeber-lenti",
    "https://apa.az/xeber-lenti?page=2",
    "https://apa.az/xeber-lenti?page=3",
    "https://apa.az/rss"
]

for menbe in menbeler:
    try:
        r = session.get(menbe, timeout=12)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'lxml')
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.startswith('https://apa.az/') and any(char.isdigit() for char in href.split('-')[-1]):
                if 'locale=' not in href and 'top-10' not in href and 'election' not in href and '/news/' not in href:
                    tapilan_linkler.add(href)
    except:
        pass

tapilan_linkler = list(tapilan_linkler)
print(f"✅ Saytdan {len(tapilan_linkler)} unikal xəbər linki aşkar edildi.")

# 2. ADDIM: ƏVVƏL YIĞILMIŞ XƏBƏRLƏRİ OXUYURUQ
csv_file = "apa_xeberler.csv"
movcud_linkler = set()
movcud_xeberler = []

if os.path.exists(csv_file):
    try:
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                link = row.get('Xəbər Linki') or row.get('Link')
                if link and link not in movcud_linkler:
                    movcud_linkler.add(link)
                    movcud_xeberler.append(row)
    except:
        pass

yeni_linkler = [u for u in tapilan_linkler if u not in movcud_linkler]
print(f"⚡ Toplanacaq YENİ xəbər sayı: {len(yeni_linkler)}")

# 3. ADDIM: YENİ XƏBƏRLƏRİ PARALEL OXUYURUQ
def bir_xeberi_oxu(url):
    try:
        r = session.get(url, timeout=10)
        r.encoding = 'utf-8'
        xeber_soup = BeautifulSoup(r.text, 'lxml')
        
        h2 = xeber_soup.find('h2')
        og_title = xeber_soup.find('meta', property='og:title')
        basliq = h2.get_text().strip() if h2 else (og_title.get('content') if og_title else "")
        if not basliq: return None
        
        h1 = xeber_soup.find('h1')
        kateqoriya = h1.get_text().strip() if h1 else "Ümumi"
        
        tarix_qutusu = xeber_soup.find(class_='date')
        tarix = re.sub(r'\s+', ' ', tarix_qutusu.get_text()).strip() if tarix_qutusu else ""
        
        metn_qutusu = xeber_soup.find('div', class_='texts')
        if metn_qutusu:
            for zibil in metn_qutusu.find_all(['script', 'style', 'iframe']):
                zibil.decompose()
            paragraflar = [re.sub(r'\s+', ' ', p.get_text()).strip() for p in metn_qutusu.find_all('p') if p.get_text().strip()]
            metn = " ".join(paragraflar)
        else:
            metn = ""
            
        return {
            'Başlıq': basliq,
            'Kateqoriya': kateqoriya,
            'Tarix': tarix,
            'Xəbər Linki': url,
            'Xəbərin Mətni': metn
        }
    except:
        return None

yeni_toplananlar = []
if yeni_linkler:
    print(f"2. Yeni xəbərlər oxunur...")
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(bir_xeberi_oxu, url): url for url in yeni_linkler}
        for f in as_completed(futures):
            res = f.result()
            if res: yeni_toplananlar.append(res)

# Bütün xəbərləri birləşdiririk
butun_xeberler = yeni_toplananlar + movcud_xeberler

# 4. ADDIM: ƏSAS TƏLƏB — YENİDƏN KÖHNƏYƏ SIRALAYIQ (DESCENDING ORDER)
print("\n3. Bütün xəbərlər YENİDƏN KÖHNƏYƏ doğru xronoloji sıralanır...")

def siralama_acari(x):
    tarix_str = x.get('Tarix') or ''
    url = x.get('Xəbər Linki') or ''
    # Xəbərin ID nömrəsi (yeni xəbərlərin ID-si həmişə daha böyük olur)
    id_match = re.search(r'-(\d{5,8})', url)
    xeber_id = int(id_match.group(1)) if id_match else 0
    
    dt = tarixi_standarta_cevir(tarix_str, url)
    # Əsasən tarixə görə, eyni tarixdədirsə ID-yə görə sıralayırıq
    return (dt if isinstance(dt, datetime) else datetime(2000, 1, 1), xeber_id)

# reverse=True -> ƏN YENİ XƏBƏR №1 OLUR!
butun_xeberler.sort(key=siralama_acari, reverse=True)

# № sütununu 1-dən sona qədər təzədən nömrələyirik
for i, x in enumerate(butun_xeberler, 1):
    x['№'] = i

print(f"✅ Sıralama tamamlandı: Cəmi {len(butun_xeberler)} xəbər (Ən yeni xəbər №1-dir).")

# 5. ADDIM: EXCEL VƏ CSV-YƏ YAZIRIQ
headers_list = ["№", "Başlıq", "Kateqoriya", "Tarix", "Xəbər Linki", "Xəbərin Mətni"]

# 1. EXCEL (.xlsx)
excel_file = "apa_xeberler.xlsx"
wb = openpyxl.Workbook()
ws = wb.active
ws.title = "APA Xəbərlər"

ws.append(headers_list)

header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
header_align = Alignment(horizontal="center", vertical="center")

for col_num in range(1, len(headers_list) + 1):
    cell = ws.cell(row=1, column=col_num)
    cell.font = header_font
    cell.fill = header_fill
    cell.alignment = header_align

for item in butun_xeberler:
    ws.append([
        item.get('№'),
        item.get('Başlıq'),
        item.get('Kateqoriya'),
        item.get('Tarix'),
        item.get('Xəbər Linki'),
        item.get('Xəbərin Mətni')
    ])

ws.column_dimensions['A'].width = 6
ws.column_dimensions['B'].width = 45
ws.column_dimensions['C'].width = 18
ws.column_dimensions['D'].width = 25
ws.column_dimensions['E'].width = 35
ws.column_dimensions['F'].width = 60

wb.save(excel_file)

# 2. CSV (.csv)
with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=headers_list)
    writer.writeheader()
    for item in butun_xeberler:
        writer.writerow({k: item.get(k, '') for k in headers_list})

print(f"✅ Fayllar yeniləndi:")
print(f"   - {excel_file}")
print(f"   - {csv_file}")
print("=" * 60)
