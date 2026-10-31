# ============================================================
# DƏRS 2: APA.AZ-DAN ÇOXLU XƏBƏRİ ÇƏKİB SƏLİQƏLİ EXCEL-Ə YAZMAQ
# ============================================================

import sys
import re
import time
import requests
from bs4 import BeautifulSoup
import csv
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

# Terminalda Azərbaycan hərfləri xəta verməsin
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
}

print("=" * 60)
print("1. APA.AZ SAYTININ ANA SƏHİFƏSİNDƏN XƏBƏR LİNKLƏRİ TAPILIR...")
print("=" * 60)

ana_sehife = requests.get("https://apa.az/", headers=headers, timeout=15)
ana_sehife.encoding = 'utf-8'

soup = BeautifulSoup(ana_sehife.text, 'lxml')

# Yalnız həqiqi xəbər linklərini seçirik
xeber_linkleri = []
for link in soup.find_all('a', href=True):
    href = link['href']
    # Xəbər linkləri: nömrə ilə bitir və lazımsız bölmələri atırıq
    if href.startswith('https://apa.az/') and any(char.isdigit() for char in href.split('-')[-1]):
        if href not in xeber_linkleri and 'locale=' not in href and 'top-10' not in href and 'election' not in href and '/news/' not in href:
            xeber_linkleri.append(href)

print(f"✅ Ana səhifədə {len(xeber_linkleri)} aktiv xəbər linki tapıldı.")

# İlk 10 xəbəri götürürük
secilen_linkler = xeber_linkleri[:10]
print(f"Biz bu {len(secilen_linkler)} xəbəri səliqəli şəkildə toplayırıq...\n")

toplanan_xeberler = []

for sira, url in enumerate(secilen_linkler, 1):
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.encoding = 'utf-8'
        
        xeber_soup = BeautifulSoup(r.text, 'lxml')
        
        # 1. Başlıq (h2 və ya og:title)
        h2 = xeber_soup.find('h2')
        og_title = xeber_soup.find('meta', property='og:title')
        basliq = h2.get_text().strip() if h2 else (og_title.get('content') if og_title else "Başlıq tapılmadı")
        
        # 2. Kateqoriya (h1)
        h1 = xeber_soup.find('h1')
        kateqoriya = h1.get_text().strip() if h1 else "Ümumi"
        
        # 3. Tarix (Boşluqları və sətir qırılmalarını təmizləyirik!)
        tarix_qutusu = xeber_soup.find(class_='date')
        if tarix_qutusu:
            tarix = re.sub(r'\s+', ' ', tarix_qutusu.get_text()).strip()
        else:
            tarix = ""
        
        # 4. Mətn (Səliqəli paraqraflar halına gətiririk)
        metn_qutusu = xeber_soup.find('div', class_='texts')
        if metn_qutusu:
            for zibil in metn_qutusu.find_all(['script', 'style', 'iframe']):
                zibil.decompose()
            paragraflar = [re.sub(r'\s+', ' ', p.get_text()).strip() for p in metn_qutusu.find_all('p') if p.get_text().strip()]
            metn = " ".join(paragraflar)  # Cədvəli dağıtmamaq üçün tək səliqəli mətn
        else:
            metn = ""
        
        toplanan_xeberler.append({
            'sira': sira,
            'basliq': basliq,
            'kateqoriya': kateqoriya,
            'tarix': tarix,
            'link': url,
            'metn': metn
        })
        
        print(f"[{sira}/10] ✓ {basliq[:50]}... ({kateqoriya})")
        time.sleep(0.3)
        
    except Exception as e:
        print(f"[{sira}/10] ✗ Xəta: {e}")

# ============================================================
# İKİ ƏDƏD ÇOX SƏLİQƏLİ FAYL YARADIRIQ:
# 1. apa_xeberler.xlsx (HƏQİQİ EXCEL FAYLI - DİZAYNLI VƏ SƏLİQƏLİ)
# 2. apa_xeberler.csv  (CSV FORMATI)
# ============================================================

print("\n" + "=" * 60)
print("MƏLUMATLAR SƏLİQƏLİ EXCEL VƏ CSV FAYLLARINA YAZILIR...")
print("=" * 60)

# --- 1. HƏQİQİ EXCEL (.xlsx) YARATMAQ ---
wb = openpyxl.Workbook()
ws = wb.active
ws.title = "APA Xəbərlər"

# Sütun adları
headers_list = ["№", "Başlıq", "Kateqoriya", "Tarix", "Xəbər Linki", "Xəbərin Mətni"]
ws.append(headers_list)

# Başlıq sətirini rəngli və gözəl edirik (Göy fon, ağ qalın yazı)
header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
header_align = Alignment(horizontal="center", vertical="center")

for col_num in range(1, len(headers_list) + 1):
    cell = ws.cell(row=1, column=col_num)
    cell.font = header_font
    cell.fill = header_fill
    cell.alignment = header_align

# Xəbərləri sətir-sətir əlavə edirik
for item in toplanan_xeberler:
    ws.append([
        item['sira'],
        item['basliq'],
        item['kateqoriya'],
        item['tarix'],
        item['link'],
        item['metn']
    ])

# Sütunların enini avtomatik tənzimləyirik ki, yazılar sıxışmasın
ws.column_dimensions['A'].width = 6
ws.column_dimensions['B'].width = 45
ws.column_dimensions['C'].width = 18
ws.column_dimensions['D'].width = 25
ws.column_dimensions['E'].width = 35
ws.column_dimensions['F'].width = 60

excel_file = "apa_xeberler.xlsx"
wb.save(excel_file)
print(f"✅ 1. Əsl Excel faylı yaradıldı: '{excel_file}' (Hər xəbər tək bir səliqəli sətirdə!)")

# --- 2. SƏLİQƏLİ CSV (.csv) YARATMAQ ---
csv_file = "apa_xeberler.csv"
with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(headers_list)
    for item in toplanan_xeberler:
        writer.writerow([
            item['sira'],
            item['basliq'],
            item['kateqoriya'],
            item['tarix'],
            item['link'],
            item['metn']
        ])
print(f"✅ 2. CSV faylı yaradıldı: '{csv_file}'")

print("\n" + "=" * 60)
print(f"🎉 HAZIRDIR! İndi birbaşa '{excel_file}' və ya '{csv_file}' faylını aç.")
print("=" * 60)
