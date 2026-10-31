# ============================================================
# APA.AZ BÜTÜN XƏBƏRLƏRİN TOPLANMASI VƏ EXCEL-Ə YAZILMASI
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

# Terminalda Azərbaycan hərfləri xəta verməsin
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
os.chdir(os.path.dirname(os.path.abspath(__file__)))

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
}

print("=" * 60)
print("APA.AZ - BÜTÜN XƏBƏRLƏRİN TOPLANMASI BAŞLAYIR...")
print("=" * 60)

session = requests.Session()
session.headers.update(headers)

# 1. ADDIM: BÜTÜN MƏNBƏLƏRDƏN XƏBƏR LİNKLƏRİNİ TOPLAYIQ
print("\n1. Bütün mənbələrdən xəbər linkləri toplanır (Ana səhifə, Xəbər lenti, RSS)...")

tapilan_linkler = set()

# Axtarılacaq əsas səhifələr (Ana səhifə, RSS və Xəbər lentinin ilk səhifələri)
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
            # APA xəbər linki: nömrə ilə bitir, locale və top-10 deyil
            if href.startswith('https://apa.az/') and any(char.isdigit() for char in href.split('-')[-1]):
                if 'locale=' not in href and 'top-10' not in href and 'election' not in href and '/news/' not in href:
                    tapilan_linkler.add(href)
    except Exception as e:
        print(f"Xəta ({menbe}): {e}")

tapilan_linkler = list(tapilan_linkler)
print(f"✅ Saytdan cəmi {len(tapilan_linkler)} unikal xəbər linki aşkar edildi!")

# 2. ADDIM: ƏVVƏL YIĞILMIŞ XƏBƏRLƏRİ YADDAŞDAN OXUYAQ (TƏKRARÇILIQ OLMASIN)
csv_file = "apa_xeberler.csv"
movcud_linkler = set()
movcud_xeberler = []

if os.path.exists(csv_file):
    try:
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                link = row.get('Xəbər Linki') or row.get('Link')
                if link:
                    movcud_linkler.add(link)
                    movcud_xeberler.append(row)
        print(f"📁 Əvvəlcədən cədvəldə olan xəbər sayı: {len(movcud_xeberler)}")
    except Exception as e:
        pass

# Yalnız hələ toplanmamış TƏZƏ xəbərləri seçək
yeni_linkler = [u for u in tapilan_linkler if u not in movcud_linkler]
print(f"⚡ Toplanacaq YENİ xəbər sayı: {len(yeni_linkler)}")

# 3. ADDIM: ÇOXAXINLI (SÜRƏTLİ) ŞƏKİLDƏ BÜTÜN YENİ XƏBƏRLƏRİ YÜKLƏYƏK
def bir_xeberi_oxu(url):
    try:
        r = session.get(url, timeout=10)
        r.encoding = 'utf-8'
        xeber_soup = BeautifulSoup(r.text, 'lxml')
        
        # Başlıq
        h2 = xeber_soup.find('h2')
        og_title = xeber_soup.find('meta', property='og:title')
        basliq = h2.get_text().strip() if h2 else (og_title.get('content') if og_title else "")
        if not basliq: return None
        
        # Kateqoriya
        h1 = xeber_soup.find('h1')
        kateqoriya = h1.get_text().strip() if h1 else "Ümumi"
        
        # Tarix
        tarix_qutusu = xeber_soup.find(class_='date')
        tarix = re.sub(r'\s+', ' ', tarix_qutusu.get_text()).strip() if tarix_qutusu else ""
        
        # Mətn
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
    print(f"\n2. Xəbərlər paralel olaraq oxunur (Worker sayı: 6)...")
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(bir_xeberi_oxu, url): url for url in yeni_linkler}
        count = 0
        for f in as_completed(futures):
            res = f.result()
            if res:
                yeni_toplananlar.append(res)
                count += 1
                if count % 10 == 0 or count == len(yeni_linkler):
                    print(f"  [{count}/{len(yeni_linkler)}] ✓ {res['Başlıq'][:55]}...")

# 4. ADDIM: BÜTÜN XƏBƏRLƏRİ BİRLƏŞDİRİB EXCEL VƏ CSV-YƏ YAZIRIQ
# Yeni xəbərləri ən başa qoyuruq ki, ən son xəbərlər birinci görünsün
butun_xeberler = yeni_toplananlar + movcud_xeberler

# Sıra nömrələrini 1-dən sona qədər yenidən düzürük
for i, x in enumerate(butun_xeberler, 1):
    x['№'] = i

print("\n" + "=" * 60)
print(f"Cəmi {len(butun_xeberler)} xəbər Excel və CSV fayllarına yazılır...")
print("=" * 60)

headers_list = ["№", "Başlıq", "Kateqoriya", "Tarix", "Xəbər Linki", "Xəbərin Mətni"]

# 1. HƏQİQİ EXCEL (.xlsx)
excel_file = "apa_xeberler.xlsx"
wb = openpyxl.Workbook()
ws = wb.active
ws.title = "APA Xəbərlər"

ws.append(headers_list)

# Başlıq dizaynı
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
print(f"✅ Excel faylı yeniləndi: '{excel_file}' (Cəmi: {len(butun_xeberler)} xəbər)")

# 2. CSV (.csv)
with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=headers_list)
    writer.writeheader()
    for item in butun_xeberler:
        writer.writerow({k: item.get(k, '') for k in headers_list})

print(f"✅ CSV faylı yeniləndi: '{csv_file}' (Cəmi: {len(butun_xeberler)} xəbər)")

print("\n" + "=" * 60)
print(f"🎉 TAMAMLANDI! Artıq 10 deyil, cəmi {len(butun_xeberler)} xəbər siyahıdadır!")
print("=" * 60)
