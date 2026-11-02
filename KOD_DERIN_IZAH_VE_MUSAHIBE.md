# 🎓 Web Scraping — Dərin Kod Təhlili, Memarlıq, Terminlər Lüğəti və Müsahibə Bələdçisi

> **Qeyd:** Bu sənəddə keçən bütün texniki və ingilisdilli terminlərin dərhal yanında mötərizədə və ya xüsusi qeydlə onların **Azərbaycan dilində sadə və anlaşıqlı izahı** verilmişdir. Beləliklə, müsahibə və ya imtahan zamanı istənilən termini çəkinmədən işlədə və mənasını anında izah edə biləcəksiniz.

---

## 📑 MÜNDƏRİCAT

1. [Əsas İT və Web Scraping Terminləri Lüğəti](#1-əsas-it-və-web-scraping-terminləri-lüğəti)
2. [Ümumi Konseptual Model və Məlumat Axını (Data Pipeline)](#2-ümumi-konseptual-model-və-məlumat-axını-data-pipeline)
3. [HTTP Protokolu, Brauzer İmitasiyası və Bloklanmadan Qorunma](#3-http-protokolu-brauzer-imitasiyası-və-bloklanmadan-qorunma)
4. [APA.AZ Skriptinin (`apa_az/main.py`) Sətirbəsətir Dərin Təhlili](#4-apaaz-skriptinin-apa_azmainpy-sətirbəsətir-dərin-təhlili)
   - [4.1. Tarix Parsingi və Normalizasiyası](#41-tarix-parsingi-və-normalizasiyası)
   - [4.2. Link Kəşfi (Discovery Engine) və Təmizləmə](#42-link-kəşfi-discovery-engine-və-təmizləmə)
   - [4.3. Deduplikasiya (Təkrarçılığın Qarşısının Alınması)](#43-deduplikasiya-təkrarçılığın-qarşısının-alınması)
   - [4.4. Çoxaxınlılıq (Concurrency / Multi-threading)](#44-çoxaxınlılıq-concurrency--multi-threading)
   - [4.5. DOM Parsing və Sanitizasiya (Zibil Teqlərin Silinməsi)](#45-dom-parsing-və-sanitizasiya-zibil-teqlərin-silinməsi)
   - [4.6. İkiqat Xronoloji Sıralama Alqoritmi](#46-ikiqat-xronoloji-sıralama-alqoritmi)
   - [4.7. Excel və CSV İxrac Mexanizmi (BOM və UTF-8)](#47-excel-və-csv-ixrac-mexanizmi-bom-və-utf-8)
5. [Report.az Layihəsinin Korporativ Memarlığı (Enterprise Architecture)](#5-reportaz-layihəsinin-korporativ-memarlığı-enterprise-architecture)
   - [5.1. SQLite və WAL (Write-Ahead Logging) Rejimi](#51-sqlite-və-wal-write-ahead-logging-rejimi)
   - [5.2. Pydantic İlə Məlumat Validasiyası](#52-pydantic-ilə-məlumat-validasiyası)
   - [5.3. Checkpoint və Crash Recovery (Qaldığı Yerdən Davam Etmə)](#53-checkpoint-və-crash-recovery-qaldığı-yerdən-davam-etmə)
6. [Müsahibə və İmtahan Sualları (Dəqiq Cavablar İlə)](#6-müsahibə-və-imtahan-sualları-dəqiq-cavablar-ilə)

---

## 1. Əsas İT və Web Scraping Terminləri Lüğəti

Hər dəfə bu sözləri eşitdikdə və ya işlətdikdə nəyi nəzərdə tutduğunuzu dəqiq bilin:

* **Web Scraping (Veb qazıma):** Veb saytların HTML kodundan lazımi məlumatları (başlıq, mətn, qiymət, tarix) avtomatlaşdırılmış şəkildə çıxarıb cədvələ və ya bazaya yığmaq prosesi.
* **Parsing (Sintaktik təhlil / Parçalama):** Qarışıq bir mətni və ya proqram kodunu hissələrə bölərək içindən bizə lazım olan konkret məlumatı tapıb ayırmaq.
* **Pipeline (Məlumat boru xətti):** Məlumatın xam haldan (məsələn, qarışıq HTML) başlayaraq emal edilib son fayla (məsələn, səliqəli Excel) çevrilənə qədər keçdiyi addımlar zənciri.
* **Deduplication (Dublikatların təmizlənməsi):** Eyni məlumatın (məsələn, eyni xəbər linkinin) bazaya və ya fayla təkrar-təkrar yazılmasının qarşısını almaq.
* **Sanitization (Təmizləmə / Sanitizasiya):** Məlumatın içindəki zərərli və ya lazımsız hissələri (reklam kodları, scriptlər, artıq boşluqlar) ayırıb silmək.
* **Concurrency / Multi-threading (Çoxaxınlılıq / Paralel iş):** Proqramın işləri tək-tək (ardıcıl) görmək əvəzinə, eyni anda bir neçə işçi qol (axın) vasitəsilə paralel görməsi.
* **I/O-Bound (Giriş-Çıxışdan / Şəbəkədən asılı iş):** Prosessorun gücündən çox, internetdən cavab gəlməsini gözləməyə sərf olunan proseslər.
* **DOM (Document Object Model):** Veb səhifənin brauzerdə ağac şəklində budaqlanan HTML quruluşu (hər bir `div`, `p`, `h1` bir budaqdır).
* **Rate Limiting (Sorğu sürəti məhdudiyyəti):** Saytın həddindən artıq tez-tez sorğu göndərən botları bloklamaq üçün qoyduğu limit.
* **BOM (Byte Order Mark - Bayt Sırası İşarəsi):** Faylın ən başına qoyulan gizli kod; Microsoft Excel kimi proqramlara faylın UTF-8 olduğunu və Azərbaycan şriftlərini düzgün göstərməli olduğunu bildirir.
* **Checkpoint (Yoxlama / Qeydiyyat nöqtəsi):** Proqram qəfil dayandıqda və ya internet kəsildikdə, sıfırdan başlamamaq üçün ən son qaldığı yeri bazaya qeyd etməsi.
* **Validation (Doğrulama / Yoxlama):** Gələn məlumatın düzgün formatda olub-olmadığını (məsələn, tarixin həqiqətən tarix olub-olmadığını) yoxlamaq.

---

## 2. Ümumi Konseptual Model və Məlumat Axını (Data Pipeline)

Bu layihədə məlumatlar xam HTML-dən son analitik fayla qədər 5 pilləli boru xəttindən (**pipeline — addımlar zəncirindən**) keçir:0.

```
[MƏRHƏLƏ 1: KƏŞF (Discovery - Linklərin Aşkarlanması)]
   ├── Saytın xəbər lenti, sitemap.xml və ya RSS-i taranır
   └── Bütün potensial xəbər URL-ləri çıxarılır
             │
             ▼
[MƏRHƏLƏ 2: DEDUPLİKASİYA (Təkrarların Təmizlənməsi)]
   ├── Mövcud baza/fayl oxunur
   └── Yalnız YENİ (əvvəl toplanmamış) URL-lər ayrılır
             │
             ▼
[MƏRHƏLƏ 3: EXTRACTION (Çoxaxınlı Yükləmə və DOM Parsing)]
   ├── ThreadPoolExecutor ilə paralel HTTP GET sorğuları göndərilir
   ├── BeautifulSoup ilə HTML ağacı qurulur
   └── Reklam/skriptlər təmizlənir, başlıq, mətn, tarix çıxarılır
             │
             ▼
[MƏRHƏLƏ 4: TRANSFORMATION (Normalizasiya və Sıralama)]
   ├── Mətn formatlı tarixlər Python 'datetime' obyektinə çevrilir
   └── İkiqat açarla sıralanır: 1) Dəqiq Tarix (DESC), 2) Xəbər ID (DESC)
             │
             ▼
[MƏRHƏLƏ 5: STORAGE / LOADING (Yaddaşa Yazma və İxrac)]
   ├── APA: Excel (.xlsx) və UTF-8-BOM CSV (.csv) fayllarına yazılır
   └── Report.az: SQLite DB (.db), JSON, JSONL və CSV fayllarına yazılır
```

---

## 3. HTTP Protokolu, Brauzer İmitasiyası və Bloklanmadan Qorunma

### Niyə sayt bizi bloklamır?
Veb serverlər (Cloudflare, Nginx kimi təhlükəsizlik sistemləri) avtomatlaşdırılmış botları dərhal tanıyır. Kodumuzda bunun qarşısını almaq üçün 3 mühüm tədbir görülüb:

#### 1. `User-Agent Header` (İstifadəçi Təmsilçisi Başlığı):
```python
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
}
```
* **Termin izahı:** `Header` (başlıq) — brauzerin sayta daxil olarkən arxa planda göndərdiyi pasport məlumatıdır.
* **Məntiqi:** Standart Python kodu sayta girəndə özünü `python-requests` adında bir bot kimi təqdim edir və server onu dərhal bloklayır. Biz isə `headers` yazaraq serverə deyirik: *"Mən Windows 10 kompüterində işləyən rəsmi Google Chrome brauzeriyəm."*

#### 2. Persistent TCP Session (`requests.Session()` — Qalıcı Şəbəkə Sessiyası):
* **Termin izahı:** `TCP Handshake` (əlaqə razılaşması) — brauzerlə server arasında hər dəfə bağlantı qurulanda baş verən salamlaşma və şifrələmə təsdiqidir.
* **Məntiqi:** Adi halda hər 100 xəbər üçün 100 dəfə sıfırdan bağlantı qurulur və bu həm vaxt aparır, həm də saytda şübhə yaradır. `session = requests.Session()` sayəsində TCP bağlantısı açıq qalır (HTTP Keep-Alive texnologiyası) və sorğular 3-5 dəfə daha sürətli icra olunur.

#### 3. `Timeout` (Vaxt Aşımı Təhlükəsizliyi):
```python
r = session.get(url, timeout=10)
```
* **Məntiqi:** Əgər server cavab verməsə və ya internet zəifləsə, proqramın saatlarla donub qalmasının qarşısını alır. 10 saniyə sonra xəta tutulur (`try/except`) və skript növbəti xəbərə keçir.

---

## 4. APA.AZ Skriptinin (`apa_az/main.py`) Sətirbəsətir Dərin Təhlili

### 4.1. Tarix Parsingi və Normalizasiyası
Saytda tarixlər belə yazılır: `"31 oktyabr 2026 18:48"`. Kompüter üçün bu sadəcə anlamsız hərflərdir və onları ardıcıl düzə bilmir.

```python
AYLAR = {
    'yanvar': 1, 'fevral': 2, 'mart': 3, 'aprel': 4,
    'may': 5, 'iyun': 6, 'iyul': 7, 'avqust': 8,
    'sentyabr': 9, 'oktyabr': 10, 'noyabr': 11, 'dekabr': 12
}

def tarixi_standarta_cevir(tarix_metni, url):
    match = re.search(r'(\d{1,2})\s+([a-zəöüğışç]+)\s+(\d{4})(?:\s+(\d{1,2}):(\d{2}))?', t_clean)
```
* **Termin izahı:** `Regex (Regular Expressions / Müntəzəm İfadələr)` — mətndə müəyyən şablona uyğun hissələri axtarıb tapan güclü axtarış dilidir.
* **Regex-in addım-addım açılışı:**
  * `(\d{1,2})` ➔ 1 və ya 2 rəqəmli gün (məsələn: `31`).
  * `\s+` ➔ Aradakı boşluq simvolu.
  * `([a-zəöüğışç]+)` ➔ Azərbaycan əlifbasındakı ay adı (məsələn: `oktyabr`).
  * `(\d{4})` ➔ 4 rəqəmli il (məsələn: `2026`).
  * `(?:\s+(\d{1,2}):(\d{2}))?` ➔ Əgər varsa saat və dəqiqə (məsələn: `18:48`).
* **Fallback (Ehtiyat mexanizm):** Əgər səhifədə tarix mətni tapılmazsa, kod URL-in sonundakı rəqəmsal xəbər ID-sini (`re.search(r'-(\d{5,8})', url)`) çıxarır. Çünki APA-da hər yeni dərc olunan xəbərin ID nömrəsi əvvəlkindən həmişə böyük olur.

---

### 4.2. Link Kəşfi (Discovery Engine) və Təmizləmə
Linklərin toplanması zamanı saytın müxtəlif səhifələri daranır:
```python
menbeler = [
    "https://apa.az/",
    "https://apa.az/xeber-lenti",
    "https://apa.az/xeber-lenti?page=2",
    "https://apa.az/xeber-lenti?page=3",
    "https://apa.az/rss"
]
```
Filtrləmə şərtinə baxaq:
```python
if href.startswith('https://apa.az/') and any(char.isdigit() for char in href.split('-')[-1]):
    if 'locale=' not in href and 'top-10' not in href and 'election' not in href and '/news/' not in href:
        tapilan_linkler.add(href)
```
* **Məntiqi:**
  1. `href.split('-')[-1]` — APA xəbər linklərinin sonunda həmişə xəbər nömrəsi olur (məsələn: `...-884123`). Əgər linkin sonunda rəqəm yoxdursa, deməli bu xəbər deyil, sadəcə menyu və ya bölmə linkidir.
  2. `locale=`, `/news/` — Saytın ingilis və rus dillərindəki bölmələrini kənarlaşdırır, yalnız təmiz Azərbaycan dilindəki xəbərləri saxlayır.

---

### 4.3. Deduplikasiya (Təkrarçılığın Qarşısının Alınması)
```python
movcud_linkler = set()
# Əvvəlki fayldakı linklər movcud_linkler içinə doldurulur...
yeni_linkler = [u for u in tapilan_linkler if u not in movcud_linkler]
```
* **Termin izahı:** `Time Complexity (Zaman Mürəkkəbliyi) — $O(1)$ vs $O(N)$`:
  * Əgər biz adi siyahı (`list`) istifadə etsəydik, hər bir linki mövcud siyahıda axtarmaq üçün Python siyahının bütün elementlərini tək-tək yoxlayacaqdı ($O(N)$ əməliyyat).
  * Biz isə `set()` (Hash-Table / Het-cədvəl) istifadə etdik. `set`-də axtarış $O(1)$-dir, yəni bazada 100,000 xəbər olsa belə, axtarış göz qırpımında (ani) baş verir.
* **Məqsəd:** Artıq faylda olan xəbərləri təkrar oxumamaq, yalnız sayta indicə çıxmış təzə xəbərləri yükləmək.

---

### 4.4. Çoxaxınlılıq (Concurrency / Multi-threading)
```python
with ThreadPoolExecutor(max_workers=6) as executor:
    futures = {executor.submit(bir_xeberi_oxu, url): url for url in yeni_linkler}
    for f in as_completed(futures):
        res = f.result()
        if res: yeni_toplananlar.append(res)
```
* **Termin izahı:**
  * `ThreadPoolExecutor`: Eyni anda bir neçə işçi axın (thread) işə salan idarəetmə mühərrikidir.
  * `max_workers=6`: Eyni anda paralel işləyən 6 işçi deməkdir.
  * `futures`: Gələcəkdə tamamlanacaq işləri saxlayan obyektlərdir.
* **Müsahibə üçün əsas arqument:** Niyə Multiprocessing yox, Multi-threading?
  * Çünki web scraping **I/O-Bound** (şəbəkə gözləməli) əməliyyatdır. Prosessor yorulmur, vaxtın 95%-i internetdən cavab gözləməyə gedir. Buna görə də ağır proseslər açmağa ehtiyac yoxdur; yüngül işçi axınlar (threads) kifayətdir.
* **Niyə məhz 6 worker?**
  * Worker sayını 50 etsək, saytın serveri bunu hücum (DDoS) kimi qəbul edib bizi bloklayar. 6 worker həm çox sürətlidir (~8 saniyəyə 50 xəbər), həm də sayt üçün tamamilə təhlükəsizdir.

---

### 4.5. DOM Parsing və Sanitizasiya (Zibil Teqlərin Silinməsi)
```python
metn_qutusu = xeber_soup.find('div', class_='texts')
if metn_qutusu:
    for zibil in metn_qutusu.find_all(['script', 'style', 'iframe']):
        zibil.decompose()
    paragraflar = [re.sub(r'\s+', ' ', p.get_text()).strip() for p in metn_qutusu.find_all('p') if p.get_text().strip()]
    metn = " ".join(paragraflar)
```
* **Termin izahı:**
  * `DOM (Document Object Model)`: Saytın HTML elementlərinin ağacvari quruluşu.
  * `.decompose()`: Tapılmış lazımsız HTML elementini kökündən kəsib yaddaşdan silən BeautifulSoup metodudur.
  * `Sanitizasiya`: Məlumatı zibil kodlardan təmizləmək.
* **Məntiqi:** Bəzən xəbər mətninin içinə reklam bannerləri (`<iframe>`) və ya sayğac kodları (`<script>`) düşür. `.decompose()` onları təmizləyir. `re.sub(r'\s+', ' ', ...)` isə sətir qırılmalarını və artıq boşluqları aradan qaldıraraq mətni təmiz, bütöv paraqrafa çevirir.

---

### 4.6. İkiqat Xronoloji Sıralama Alqoritmi
Layihənin ən kritik tələbi: **Ən yeni xəbər cədvəldə həmişə №1 olmalıdır.**

```python
def siralama_acari(x):
    tarix_str = x.get('Tarix') or ''
    url = x.get('Xəbər Linki') or ''
    id_match = re.search(r'-(\d{5,8})', url)
    xeber_id = int(id_match.group(1)) if id_match else 0
    dt = tarixi_standarta_cevir(tarix_str, url)
    return (dt if isinstance(dt, datetime) else datetime(2000, 1, 1), xeber_id)

butun_xeberler.sort(key=siralama_acari, reverse=True)
```
* **Problem:** İki fərqli xəbər tam eyni dəqiqədə dərc oluna bilər (məsələn, hər ikisi saat `11:45`-də). Kompüter hansının daha yeni olduğunu necə biləcək?
* **Həll yolu (İkiqat açar):** Biz sıralama açarı kimi Python-da ikili dəyər (`tuple`) qaytarırıq: `(Dəqiq_Tarix, Xeber_ID)`.
  1. Əvvəlcə tarixlər müqayisə olunur.
  2. Əgər tarixlər bərabərdirsə, xəbərin ID nömrəsinə baxılır. ID-si böyük olan xəbər daha sonra çıxdığı üçün ən başa keçir.
* `reverse=True` (Tərs sıralama): Böyükdən kiçiyə düzür (yəni ən yeni xəbər 1-ci olur).
* `enumerate(butun_xeberler, 1)` vasitəsilə 1-dən sona qədər sıra nömrələri verilir.

---

### 4.7. Excel və CSV İxrac Mexanizmi (BOM və UTF-8)
* **Excel Stili (`openpyxl`):**
  Cədvəlin 1-ci sətrinə tünd göy rəng (`#1F497D`), ağ və qalın şrift (`Font(color="FFFFFF", bold=True)`), mərkəzə düzləndirmə verilir. Sütunların eni məzmunun rahat oxunması üçün xüsusi nizamlanır (`column_dimensions['B'].width = 45`).
* **CSV Kodlaşdırması (`encoding='utf-8-sig'`):**
  * **Termin izahı:** `UTF-8-SIG` — faylın ən əvvəlinə **BOM (Byte Order Mark)** adlı görünməz 3 baytlıq xüsusi imza əlavə edir.
  * **Məntiqi:** Əgər sadə `utf-8` yazsaydıq, Windows və Microsoft Excel Azərbaycan hərflərini (ə, ı, ö, ğ, ç, ş) tanımayıb pozacaqdı (məsələn, "Ã§", "ÄŸ" kimi). `utf-8-sig` Excel-ə məcbur edir ki, hərfləri Azərbaycan dilində təmiz göstərsin.

---

## 5. Report.az Layihəsinin Korporativ Memarlığı (Enterprise Architecture)

Report.az layihəsi böyük məlumat həcmi (on minlərlə xəbər) üçün nəzərdə tutulmuş çoxmodullu peşəkar sistemdir.

### 5.1. SQLite və WAL (Write-Ahead Logging) Rejimi
* **Termin izahı:** `WAL (Write-Ahead Logging)` — Verilənlər bazasının yazma və oxuma əməliyyatlarını paralel aparması üçün xüsusi iş rejimidir.
* **Məntiqi:** Adi SQLite-da bir axın bazaya məlumat yazanda bütün baza kilidlənir (`database is locked` xətası yaranır). WAL rejimində isə bir tərəfdən yeni xəbərlər bazaya axarkən, digər tərəfdən başqa skriptlər heç bir donma olmadan məlumatları oxuya bilir.
* `PRAGMA synchronous = NORMAL`: Diskə yazma sürətini bir neçə dəfə artırır.

### 5.2. Pydantic İlə Məlumat Validasiyası (`models.py`)
* **Termin izahı:** `Validation (Doğrulama)` — Gələn məlumatların keyfiyyət və tip nəzarətindən keçirilməsi.
* **Məntiqi:** Saytdan bəzən başlığı olmayan, mətni boş və ya linki xarab xəbərlər gələ bilər. `Pydantic` kitabxanası xəbərləri bazaya buraxmazdan əvvəl "gömrük nəzarətçisi" kimi yoxlayır; formatı pozulmuş xəbərləri bloklayır və bazanın təmizliyini qoruyur.

### 5.3. Checkpoint və Crash Recovery (Qaldığı Yerdən Davam Etmə)
* **Termin izahı:** `Fault-Tolerance (Xətalara Dözümlülük)` — Kompüter söndükdə və ya internet kəsildikdə proqramın zədələnməməsi və sıfırlanmaması qabiliyyəti.
* **Məntiqi:** Verilənlər bazasında hər URL üçün status qeyd olunur:
  * `pending` — növbədə gözləyən linklər;
  * `scraped` — uğurla oxunub bazaya yazılmış xəbərlər;
  * `failed` — açılmayan və ya silinmiş xəbərlər.
* Skript yenidən işə düşəndə artıq oxunmuşları keçir, yalnız `pending` olanları oxumağa davam edir.

---

## 6. Müsahibə və İmtahan Sualları (Dəqiq Cavablar İlə)

Bu suallar müsahibələrdə web scraping layihələri üzrə ən çox verilən suallardır:

#### ❓ Sual 1: "Layihənizdə Concurrency (paralellik) necə təşkil olunub və hansı faydanı verir?"
> **Cavab:** Layihədə `concurrent.futures.ThreadPoolExecutor` istifadə etmişik. Web scraping I/O-bound (şəbəkə gözləməli) proses olduğu üçün, 6 paralel işçi axın (worker thread) yaratmışıq. Bu, hər xəbəri ardıcıl gözləmək əvəzinə, şəbəkə gecikmələrini paralel idarə edir və ümumi scraping vaxtını təxminən 5–6 dəfə azaldır.

#### ❓ Sual 2: "Xəbərlərin ən yenidən köhnəyə xronoloji sıralanmasını necə təmin etdiniz?"
> **Cavab:** Saytdakı mətn formatlı tarixləri Regex və ay lüğəti vasitəsilə Python-un `datetime` obyektinə çevirdik. Sıralama zamanı isə `(datetime, xeber_id)` şəklində ikili açardan (`tuple`) istifadə etdik. Əgər iki xəbər eyni dəqiqədə çıxıbsa, xəbər ID-sinin böyüklüyünə görə ən son çıxan xəbər birinci yerə qoyulur (`reverse=True`).

#### ❓ Sual 3: "Deduplikasiyanı (dublikatların qarşısının alınmasını) necə həll etmisiniz?"
> **Cavab:** Saytdan tapılan linkləri Python `set()` kolleksiyasında saxlayırıq ki, səhifədə təkrarlanan linklər süzülsün. Daha sonra mövcud baza və ya CSV-dəki linkləri də `set` içinə alaraq $O(1)$ zaman mürəkkəbliyi ilə yalnız faylda olmayan YENİ linkləri müəyyənləşdiririk (`if url not in movcud_linkler`).

#### ❓ Sual 4: "Mətndəki reklamları, skriptləri və format xətalarını necə təmizlədiniz?"
> **Cavab:** BeautifulSoup kitabxanasının `.decompose()` funksiyası ilə məqalə daxilindəki `<script>`, `<style>` və `<iframe>` DOM elementlərini kökündən sildik. Ardınca `re.sub(r'\s+', ' ', ...)` ilə artıq boşluqları və sətir qırılmalarını tək boşluqla əvəz edərək təmiz mətn aldıq.

#### ❓ Sual 5: "Excel-də Azərbaycan hərflərinin pozulmaması üçün hansı mühəndislik həllini tətbiq etdiniz?"
> **Cavab:** CSV fayllarına yazarkən `utf-8-sig` kodlaşdırmasından istifadə etdik. Bu, faylın əvvəlinə BOM (Byte Order Mark) əlavə edərək Microsoft Excel-in Azərbaycan dilindəki hərfləri (ə, ı, ö, ğ, ç, ş) birbaşa və qüsursuz tanımasını təmin edir. Həmçinin `openpyxl` vasitəsilə formatlanmış rəsmi `.xlsx` faylı generasiya etdik.

---

> 💡 **Tövsiyə:** Bu bələdçi həm layihənizi mükəmməl dərk etmək, həm də istənilən texniki söhbətdə mövzunu peşəkar kimi idarə etmək üçün tam bələdçinizdir!

