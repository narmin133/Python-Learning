# 🇦🇿 Python Web Scraping Layihələri

Bu layihədə Azərbaycanın iki böyük xəbər agentliyinin (**Report.az** və **APA.az**) avtomatlaşdırılmış Web Scraping sistemləri yerləşir.

---

## 📁 Qovluq Strukturu

Layihə iki müstəqil və səliqəli qovluğa bölünüb:

```text
Python-Learning/
│
├── 📂 apa_az/                 <-- APA.AZ XƏBƏR SCRAPERİ
│   ├── main.py                # APA.az-dan son xəbərləri çəkən əsas skript
│   ├── apa_xeberler.xlsx      # Ən son xəbərlər (Dizaynlı Microsoft Excel faylı)
│   └── apa_xeberler.csv       # Ən son xəbərlər (CSV cədvəli)
│
├── 📂 report_az/              <-- REPORT.AZ XƏBƏR ARXİVİ SCRAPERİ
│   ├── main.py                # 1.3 milyonluq arxiv scraperi və CLI mərkəzi
│   ├── database.py            # SQLite verilənlər bazası idarəetməsi
│   ├── output/                # Çıxarılmış xəbərlər (CSV, JSON, JSONL)
│   └── README.md              # Report.az layihəsinin ətraflı təlimatı
│
└── 📄 WEB_SCRAPING_REHBERI.md  # Sıfırdan başlayanlar üçün sadə dilli bələdçi
```

---

## 🚀 Hansı Saytı Necə İşə Salmalı?

### 1️⃣ APA.az xəbərlərini yeniləmək üçün:
Terminalda yazın:
```bash
python apa_az/main.py
```
*(Nəticə dərhal `apa_az/apa_xeberler.xlsx` faylında hazır olacaq)*

---

### 2️⃣ Report.az xəbərlərini yeniləmək üçün:
Terminalda yazın:
```bash
python report_az/main.py --mode incremental
```
*(Nəticə dərhal `report_az/output/articles.csv` faylında yenilənəcək)*
