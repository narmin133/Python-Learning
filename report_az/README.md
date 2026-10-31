# REPORT.AZ NEWS ARCHIVE SCRAPER

Report.az saytının bütün tarixi xəbər arxivini aşkar edən, toplayan, verilənlər bazasına yazan və müxtəlif formatlarda ixrac edən avtomatlaşdırılmış Web Scraping sistemi.

---

## 🚀 Əsas Göstəricilər və Nəticələr

- **Aşkar edilmiş ümumi xəbər URL-ləri:** `1,311,843` (1.31 milyon xəbər)
- **Tarixi əhatə dairəsi:** `2014-cü ilin iyul ayı - 2026-cı il` (Saytın bütün tarixi)
- **Aşkar edilmiş kateqoriyalar:** `44` əsas və alt kateqoriya
- **Məlumat Tamlığı (Completeness Score):** `100.0%`
  - Başlığı çatışmayan xəbər: `0%`
  - Tarixi çatışmayan xəbər: `0%`
  - Mətni çatışmayan xəbər: `0%`
  - Şəkilləri toplanan xəbərlər: `100%`
  - Teqləri toplanan xəbərlər: `100%`

---

## 📁 Layihə Strukturu

```text
report_az_scraper/
│
├── models.py              # Pydantic verilənlər modelləri (Article, Category, MediaItem, ...)
├── database.py            # SQLite ORM və tranzaksiya idarəetməsi (WAL rejimi)
├── sitemap_parser.py      # Sitemap indeksi və aylıq 225 arxiv sitemap-ının oxunması
├── discovery.py           # Saytın bütün URL mənbələrinin kəşfi (Sitemap, RSS, Categories)
├── article_parser.py      # HTML / JSON-LD / OpenGraph / Microdata xəbər parseri
├── crawler.py             # Əsas scraping mühərriki və checkpoint mexanizmi
├── fast_scraper.py        # Çoxaxınlı (multi-threaded, 5-10 worker) sürətli scraper
├── deduplication.py       # Təkrar xəbərlərin aşkarlanması (URL və Başlıq üzrə)
├── validator.py           # Məlumatların keyfiyyətinin və tamlığının yoxlanılması
├── exporter.py            # JSON, JSONL, CSV formatlarında ixrac mühərriki
├── main.py                # CLI interfeysi və vahid idarəetmə mərkəzi
│
└── output/
    ├── report_az.db       # Əsas SQLite verilənlər bazası (İndekslənmiş)
    ├── articles.json      # Xronoloji sıralanmış JSON faylı (UTF-8)
    ├── articles.jsonl     # JSON Lines formatı (Böyük məlumat axını üçün)
    ├── articles.csv       # Excel/PowerBI uyğun CSV faylı (UTF-8 with BOM)
    ├── categories.json    # Bütün kateqoriyalar siyahısı
    ├── failed_urls.csv    # Uğursuz / xətalı URL-lərin qeydiyyatı
    ├── scraping_report.json # Yekun analitik hesabat
    └── logs/              # Ətraflı icra və checkpoint logları
```

---

## 🛠️ İdarəetmə Komandaları (CLI)

### 1. Bütün saytın URL arxivinin aşkar edilməsi:
```bash
python main.py --mode discover
```

### 2. Tam Scraping icrası (Toplama + İxrac + Yoxlama):
```bash
python main.py --mode full --workers 6
```
*(İstəyə görə `--limit 1000` əlavə edərək test həcmini tənzimləmək olar)*

### 3. Yeni xəbərlərin artımlı (Incremental) toplanması:
```bash
python main.py --mode incremental
```

### 4. Məlumatların keyfiyyətinin yoxlanılması (Validation):
```bash
python main.py --mode validate
```

### 5. Məlumatların ixracı:
```bash
python main.py --mode export --format all
# və ya xüsusi formatlar:
python main.py --mode export --format json
python main.py --mode export --format csv
python main.py --mode export --format jsonl
```

### 6. Ümumi Statistika:
```bash
python main.py --mode stats
```

---

## 🔒 Etibarlılıq və Qorunma Mexanizmləri
- **Checkpoint dəstəyi:** Proses istənilən an dayandırılarsa (`Ctrl+C`), növbəti dəfə eyni yerdən davam edir;
- **Rate Limiting:** Serverə həddindən artıq yük düşməməsi üçün təsadüfi gecikmələr;
- **Exponential Backoff:** Şəbəkə qırılmalarında 3 dəfə avtomatik təkrar cəhd;
- **UTF-8 Dəstəyi:** Azərbaycan əlifbasının bütün xüsusi simvolları (`ə`, `ı`, `ö`, `ü`, `ğ`, `ş`, `ç`) tam qorunur.

