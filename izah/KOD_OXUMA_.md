# 🧭 Web Scraping Kodunu Oxuma və Anlama Bələdçisi

Bu təlimat bu layihədəki bütün veb qazıma (web scraping) kodlarını — **`apa_az`** və **`report_az`** sistemlərini sətirbəsətir necə oxumağı, məntiqini anlamağı və istənilən Python scraping kodunu sərbəst təhlil etməyi öyrətmək üçün hazırlanmışdır.

---

## 📑 Mündəricat
1. [Ümumi Məntiq: Web Scraper Necə Düşünür?](#1-ümumi-məntiq-web-scraper-necə-düşünür)
2. [Layihədə İstifadən Olunan Əsas Kitabxanalar](#2-layihədə-istifadən-olunan-əsas-kitabxanalar)
3. [APA.AZ Skriptinin (`apa_az/main.py`) Sətirbəsətir İzahı](#3-apaaz-skriptinin-apa_azmainpy-sətirbəsətir-izahı)
4. [Report.az Layihəsinin Arxitekturası](#4-reportaz-layihəsinin-arxitekturası)
5. [Kodda Tez-tez Görəcəyiniz Xüsusi Fəndlər](#5-kodda-tez-tez-görəcəyiniz-xüsusi-fəndlər)
6. [Özün üçün Qısa Əzbər / Xülasə](#6-özün-üçün-qısa-əzbər--xülasə)

---

## 1. Ümumi Məntiq: Web Scraper Necə Düşünür?

İstənilən veb scraper əslində **brauzerdə oturan insanın etdiklərini avtomatlaşdıran** bir proqramdır:

```
[1. Sayta Daxil Olmaq] ➔ [2. Linkləri Tapmaq] ➔ [3. Xəbərə Girib Mətni Kopyalamaq] ➔ [4. Excel/CSV-yə Yazmaq]
     (requests)               (BeautifulSoup)            (find, get_text, regex)           (openpyxl, csv)
```

Bu 4 addımı yadda saxlasanız, hər hansı bir scraping kodunu oxuyanda həmişə özünüzə bu sualı verəcəksiniz: **"Hazırda kod hansı addımı icra edir?"**

---

## 2. Layihədə İstifadən Olunan Əsas Kitabxanalar

Kodun ən yuxarısındakı `import` hissəsi kodun hansı alətlərdən istifadə etdiyini göstərir:

| Kitabxana / Modul | Nə İş Görür? | Gündəlik Həyat Analoqu |
| :--- | :--- | :--- |
| `requests` | Sayta sorğu (GET request) göndərir və HTML səhifəni yükləyir | Saytın linkini brauzerin ünvan yerinə yazıb "Enter" vurmaq |
| `BeautifulSoup (bs4)` | Yüklənmiş HTML kodunun içindən istədiyimiz teqləri (`h1`, `p`, `a`) axtarır | Saytda `Ctrl + F` edib istədiyin hissəni tapmaq |
| `re` (Regex) | Mətnin içindən şablona uyğun hissələri çıxarır (məs: tarixdən saatı, linkdən xəbər ID-sini) | Süzgəcdən keçirmək |
| `ThreadPoolExecutor` | Eyni anda bir neçə xəbəri paralel yükləyir (çoxaxınlı iş) | 1 nəfərin əvəzinə eyni vaxtda 6 nəfərin xəbərləri açması |
| `openpyxl` / `csv` | Toplanan məlumatları Excel (`.xlsx`) və ya `.csv` cədvəlinə yazır | Excel vərəqinə qeyd etmək |
| `datetime` | Tarixləri müqayisə etmək və xronoloji sıralamaq üçün | Təqvim və saat |

---

## 3. APA.AZ Skriptinin (`apa_az/main.py`) Sətirbəsətir İzahı

Gəlin real kod üzərindən addım-addım gedək:

### 🔹 Hissə 1: Saytın Bizi Robot Kimi Bloklamaması Üçün Başlıqlar (Headers)
```python
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
}
session = requests.Session()
session.headers.update(headers)
```
- **İzahı:** Saytlar çox vaxt avtomatlaşdırılmış skriptləri bloklayır. `User-Agent` sayta deyir ki: *"Mən Python botu deyiləm, adi Windows kompüterində Chrome brauzeri ilə girən insanam."*
- `requests.Session()` isə təkrar-təkrar əlaqə qurmaq əvəzinə ümumi sessiyanı açıq saxlayır və prosesi sürətləndirir.

---

### 🔹 Hissə 2: Tarixi Standartlaşdırma Funksiyası (`tarixi_standarta_cevir`)
```python
AYLAR = {'yanvar': 1, 'fevral': 2, ..., 'noyabr': 11, 'dekabr': 12}

def tarixi_standarta_cevir(tarix_metni, url):
    match = re.search(r'(\d{1,2})\s+([a-zəöüğışç]+)\s+(\d{4})(?:\s+(\d{1,2}):(\d{2}))?', t_clean)
```
- **Niyə lazımdır?** Çünki saytda tarix `"02 noyabr 2026 09:30"` kimi yazılıb. Kompüter bu sözləri birbaşa böyükdən-kiçiyə sıralaya bilmir.
- Funksiya:
  1. Gün, ay adı, il və saatı tapır.
  2. `AYLAR['noyabr']` vasitəsilə ayı `11` rəqəminə çevirir.
  3. Nəticədə `datetime(2026, 11, 2, 9, 30)` Python tarix obyekti yaradır. Bu obyektləri asanlıqla ən yenidən köhnəyə sıralamaq olur.

---

### 🔹 Hissə 3: 1-ci Addım — Linklərin Yığılması
```python
tapilan_linkler = set()
menbeler = [
    "https://apa.az/",
    "https://apa.az/xeber-lenti",
    "https://apa.az/xeber-lenti?page=2",
    "https://apa.az/xeber-lenti?page=3",
    "https://apa.az/rss"
]

for menbe in menbeler:
    r = session.get(menbe, timeout=12)
    soup = BeautifulSoup(r.text, 'lxml')
    for a in soup.find_all('a', href=True):
        href = a['href']
        if href.startswith('https://apa.az/') and any(char.isdigit() for char in href.split('-')[-1]):
            tapilan_linkler.add(href)
```
- **Kodu necə oxumalıyıq?**
  - `set()` — Dublikatların qarşısını alan unikal siyahıdır. Eyni link 5 dəfə qarşıya çıxsa da, bazada cəmi 1 dəfə saxlanacaq.
  - `soup.find_all('a', href=True)` — Səhifədəki bütün kliklənə bilən linkləri (`<a href="...">`) tapır.
  - `href.split('-')[-1]` — APA-nın xəbər linklərinin sonunda həmişə xəbərin ID rəqəmi olur (məsələn: `...-884123`). Şərt yoxlayır ki, link həqiqətən xəbər linkidirmi (reklam və ya menyu linki deyil).

---

### 🔹 Hissə 4: 2-ci Addım — Təkrarçılığın Qarşısının Alınması (Deduplication)
```python
yeni_linkler = [u for u in tapilan_linkler if u not in movcud_linkler]
```
- **Məntiq:** Əvvəllər toplanıb faylda olan xəbərləri təkrar oxumuruq! Saytdan tapdığımız 50 linkdən artıq 30-u faylımızda varsa, skript yalnız qalan **20 yeni linki** yükləməyə göndərir. Bu, vaxta və internetə qənaət edir.

---

### 🔹 Hissə 5: 3-cü Addım — Bir Xəbərin Məzmununu Oxumaq (`bir_xeberi_oxu`)
```python
def bir_xeberi_oxu(url):
    r = session.get(url, timeout=10)
    xeber_soup = BeautifulSoup(r.text, 'lxml')
    
    # 1. Başlıq: <h2> teqindən oxunur
    h2 = xeber_soup.find('h2')
    basliq = h2.get_text().strip() if h2 else ""
    
    # 2. Kateqoriya: <h1> teqindən oxunur
    h1 = xeber_soup.find('h1')
    kateqoriya = h1.get_text().strip() if h1 else "Ümumi"
    
    # 3. Tarix: class='date' olan elementdən oxunur
    tarix_qutusu = xeber_soup.find(class_='date')
    tarix = tarix_qutusu.get_text().strip() if tarix_qutusu else ""
    
    # 4. Mətn: <div class='texts'> daxilindəki bütün <p> (paraqraflar)
    metn_qutusu = xeber_soup.find('div', class_='texts')
    if metn_qutusu:
        for zibil in metn_qutusu.find_all(['script', 'style', 'iframe']):
            zibil.decompose() # Lazımsız skriptləri silirik
        paragraflar = [p.get_text().strip() for p in metn_qutusu.find_all('p')]
        metn = " ".join(paragraflar)
```
- **Kodu necə təhlil edirik?**
  - Brauzerdə xəbərə `Sağ klik -> Inspect (İncələ)` edəndə görürük ki, başlıq `<h2>` içindədir, tarix `.date` sinfindədir, mətn isə `.texts` içindədir. Kod məhz həmin HTML teqlərini hədəf alır.
  - `zibil.decompose()` — Mətnin içinə düşə biləcək reklam kodlarını, bannerləri və JavaScript-ləri təmizləyir.

---

### 🔹 Hissə 6: Sürətli Yükləmə (ThreadPoolExecutor)
```python
with ThreadPoolExecutor(max_workers=6) as executor:
    futures = {executor.submit(bir_xeberi_oxu, url): url for url in yeni_linkler}
    for f in as_completed(futures):
        res = f.result()
        if res: yeni_toplananlar.append(res)
```
- Əgər 50 xəbər varsa və hər xəbər 1 saniyə çəkirsə:
  - Tək axınla: 50 saniyə çəkərdi.
  - `max_workers=6` ilə: Eyni anda 6 xəbər oxunur və cəmi ~8 saniyəyə bitir!

---

### 🔹 Hissə 7: Sıralama və Excel/CSV-yə Qeyd Etmə
```python
butun_xeberler.sort(key=siralama_acari, reverse=True)
```
- `reverse=True` — Ən yeni xəbəri ən başa (1-ci sıraya) qoyur.
- Ardınca `openpyxl` vasitəsilə səliqəli göy başlıqlı Excel cədvəli yaradılır, `csv` ilə isə UTF-8 formatlı cədvəl faylı yazılır.

---

## 4. Report.az Layihəsinin Arxitekturası

Report.az daha böyük və modulyar bir sistemdir. `report_az/` qovluğunda kodlar ayrı-ayrı fayllara bölünüb:

```
report_az/
├── discovery.py         # Saytdan yeni linkləri tapan modul (Sitemap və RSS)
├── article_parser.py    # Report.az-ın HTML səhifəsini təhlil edən modul
├── database.py          # SQLite verilənlər bazası ilə işləyən hissə (report_az.db)
├── exporter.py          # Bazadakı xəbərləri CSV, JSON, JSONL fayllarına çıxaran modul
├── fix_and_refresh_az.py# Yalnız Azərbaycan dilindəki xəbərləri toplayan əsas skript
└── output/              # Nəticə fayllarının yığıldığı qovluq
```

### 🧠 Niyə SQLite bazasından istifadə olunub?
APA-da məlumat birbaşa CSV-yə yazılır. Lakin Report.az-da on minlərlə xəbər ola bilər. Əgər internet kəsilsə və ya kompüter sönsə:
- `database.py` sayəsində qaldığı yer yadda qalır (`checkpoint`).
- Növbəti dəfə skript işləyəndə artıq toplanmış xəbərləri sıfırdan toplamır, yarımçıq qalan yerdən davam edir.

---

## 5. Kodda Tez-tez Görəcəyiniz Xüsusi Fəndlər

Python kodlarını oxuyarkən bu işarələri və ifadələri görəndə nə demək olduğunu dərhal biləcəksiniz:

1. **`if __name__ == '__main__':`**
   - *Mənası:* "Bu fayl birbaşa işə salınıbsa, altındakı kodları icra et. Yox əgər başqa fayl bunu sadəcə `import` edibsə, avtomatik icra etmə."
2. **List Comprehension (Qısa dövr):**
   - Kod: `[p.get_text() for p in teqler if p.get_text()]`
   - *Açılışı:* Bütün teqləri bir-bir gəz, mətni boş olmayanların mətnini götürüb yeni siyahı düzəlt.
3. **Üçlü Şərt (Ternary Operator):**
   - Kod: `basliq = h2.get_text() if h2 else ""`
   - *Açılışı:* Əgər səhifədə `h2` tapıldisa, onun mətnini götür, tapılmadısa xəta vermə, yerinə boş mətn `""` qoy.
4. **`try ... except:`**
   - *Mənası:* Əgər hər hansı bir xəbər silinibdirsə və ya internet kəsilibsə, bütün proqram dayanmasın, o xətanı keçib növbəti xəbərə baxsın.

---

## 6. Özün üçün Qısa Əzbər / Xülasə

Gələcəkdə yeni bir xəbər saytı (məsələn, *oxu.az*, *qafqazinfo.az*) üçün kod yazmaq və ya hazır kodu oxumaq istəsəniz, diqqət edəcəyiniz **4 qızıl addım**:

1. **Link hardan tapılır?** (`sitemap.xml`, `/son-xeberler` və ya `rss`).
2. **HTML haradan oxunur?** (Brauzerdə `Inspect` edib başlıq, mətn və tarixin hansı `class` və ya `id` içində olduğunu müəyyən etmək).
3. **Tarix necə çevrilir?** (Ay adlarını rəqəmə çevirib xronoloji ardıcıllıq qurmaq).
4. **Harada saxlanılır?** (Sadə layihələrdə `CSV/Excel`, böyük layihələrdə `SQLite`).

---

> 💡 **Məsləhət:** Bu bələdçini oxuduqdan sonra `apa_az/main.py` faylını açın və yuxarıdan aşağı bu təlimatla paralel müqayisə edərək nəzərdən keçirin. Kodun hər bir sətri sizə aydın və tanış gələcək!

