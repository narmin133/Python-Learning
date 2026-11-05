# SADƏ DİLDƏ WEB SCRAPING NƏDİR VƏ BİZ NƏ ETDİK?
*(Heç bir texniki biliyi olmayanlar üçün bələdçi)*

Salam! Əgər sən proqramlaşdırmanı və texniki terminləri dərindən bilmirsənsə, **heç narahat olma**. 
Bu sənəddə mən sənə bir dost kimi, ən sadə həyati nümunələrlə başa salacağam ki, biz Report.az saytında nə etdik və sən gələcəkdə bunu özün necə edə bilərsən.

---

## 1. Web Scraping Nədir? (Kitabxanaçı nümunəsi)

Təsəvvür et ki, qarşında böyük bir kitabxana və 10 ilin qəzetləri var.
Sənə deyirlər: *"Bu qəzetlərdəki bütün xəbərləri bir-bir oxu, başlıqlarını, tarixlərini və mətnlərini bir dəftərə köçür."*

Əgər bunu **əllə (manual)** etsən:
- Hər xəbəri açmaq, mətni kopyalamaq, Word-ə yapışdırmaq üçün aylarla vaxtın gedər.
- Əlin yorular, diqqətin qaçar, səhvlər edərsən.

**Web Scraping (Veb Skreypinq) nədir?**
Web scraping — sənin yerinə bu işi görən **super-sürətli bir robot katibdir**. 
Sən ona deyirsən: *"Bu sayta get, bütün xəbərləri saniyədə 10 dənə olmaqla oxu və səliqəli şəkildə Excel cədvəlinə doldur."* 
Vəssalam! Robot bunu cəmi bir neçə dəqiqəyə edir.

---

## 2. Biz Report.az-da 1.3 Milyon Xəbəri Necə Tapdıq? (Məzmun Kataloqu)

Təsəvvür et ki, 5 mərtəbəli böyük bir marketə girmisən və sənə lazım olan məhsulları axtarırsan. 
Bütün rəfləri tək-tək gəzsən, saatlarla vaxt itirərsən. Amma marketin girişində **"Bütün Məhsulların Kataloqu"** adlı bir kitabça var. Sən o kitabçanı açırsan və dərhal görürsən ki, hansı məhsul hansı rəfdədir.

Veb-saytlarda da belə bir gizli kitabça olur. Buna texniki dildə **`sitemap.xml` (saytın xəritəsi)** deyilir.
Saytın sahibi özü Google axtarış sistemi üçün bu siyahını hazırlayıb ora qoyur.

Biz nə etdik?
1. Report.az saytının gizli xəritəsini (`https://report.az/sitemap.xml`) tapdıq.
2. Gördük ki, saytın sahibi **2014-cü ildən 2026-cı ilə qədər** hər ayın xəbərlərini ayrı-ayrı səliqəli zərflərə yığıb (cəmi 225 ədəd zərf).
3. Robotumuza dedik: *"Bu 225 zərfin hamısını aç və içindəki bütün xəbər linklərini siyahıya yaz."*
4. Cəmi **2 dəqiqə 25 saniyəyə** robot saytdakı **1,311,843 (1.31 milyon) xəbərin** linkini tapıb dəftərinə qeyd etdi.

---

## 3. "Niyə articles.csv Azərbaycanca deyildi?" (Tərcüməçi səhvi)

Sən haqlı olaraq soruşdun: *"Bu faylda yazılar niyə qəribə simvollarla çıxıb (`AzÉ™rbaycanda...`)?"*

Bunu belə başa düş:
Təsəvvür et ki, sənə təmiz Azərbaycan dilində yazılmış bir məktub gəlib (`Əhməd, gəl görüşək`). 
Amma sən bu məktubu ingilis və ya fransız əlifbasından başqa heç nə bilməyən bir adama verirsən ki, ucadan oxusun. O adam bizim **"ə", "ı", "ö", "ü", "ğ", "ş", "ç"** hərflərini tanımır. Və "ə" hərfi görəndə onu öz bildiyi qəribə simvollarla oxuyur: `É™`.

Python proqramı da ilk dəfə səhifəni açanda elə bildi ki, bu ingilis dilidir (texniki adı: `ISO-8859-1`).
Biz ona xəbərdarlıq etdik: **"Dayan! Bu ingiliscə deyil, bu zəngin Azərbaycan əlifbasıdır (`UTF-8`)!"**
Biz həmin tənzimləməni edən kimi, proqram dərhal bütün hərfləri təmiz Azərbaycan dilində yazmağa başladı.

Həmçinin Report.az saytında xəbərlər 3 dildə çıxır: Azərbaycan, Rus və İngilis. Biz robota dedik ki, **əsasən Azərbaycan dilində olan xəbərləri yığsın və cədvəlin ən başına qoysun**.

---

## 4. Xəbərin İçindən Başlıq və Mətni Necə Ayırdıq? (Qəzet dizaynı)

Qəzeti əlinə alanda sən necə bilirsən ki, hansı söz başlıqdır, hansı söz xəbərin özüdür?
- Ən böyük və qalın şriftlə yazılan söz: **Başlıqdır**.
- Şəklin altındakı kiçik ad: **Müəllifdir / Fotoqrafdır**.
- Aşağıdakı uzun paraqraflar: **Xəbərin mətnidir**.

Veb-saytlarda da eynilə belə "qutular" və "etiketlər" var:
- Başlıq həmişə **`<h1>`** adlı böyük qutunun içinə qoyulur.
- Mətn həmişə **`news-detail__desc`** adlı xüsusi məqalə qutusunun içinə qoyulur.
- Dərc olunma saatı isə **`date`** etiketinin içində saxlanılır.

Bizim robot hər səhifəni açanda birbaşa həmin qutulara baxır:
1. `<h1>` qutusundan başlığı götürür.
2. `date` qutusundan saatı və tarixi götürür.
3. `news-detail__desc` qutusundan xəbərin bütün abzaslarını götürür.
4. Reklamları və lazımsız düymələri zibil qutusuna atır.

---

## 5. Baza (Database) Niyə Lazım Oldu? (Dəmir arxiv şkafı)

Təsəvvür et ki, sənin 1.3 milyon ədəd kağız sənədin var. Sən onları bir masanın üstünə töksən, otaqda yer qalmaz, masan qırılar, axtardığını tapa bilməzsən.
Əgər onları adi bir Word və ya Notepad faylına yazsaydıq:
- Kompüter donardı.
- İşıq sönsəydi və ya internet kəsilsəydi, bütün zəhmət batardı.

Ona görə biz **SQLite** adlı elektron arxiv bazası yaratdıq (`report_az.db`).
Bu, qıfıllı dəmir arxiv şkafı kimidir:
- Hər xəbərə unikal bir nömrə (ID) verilir.
- Eyni xəbər ikinci dəfə gələndə şkaf onu içəri buraxmır (təkrarçılıq olmur).
- Əgər sən proqramı istənilən an dayandırsan (`Ctrl+C`), sabah proqramı açanda o **qaldığı xəbərdən davam edir**, heç nə itmir.

---

## 6. Çoxaxınlılıq (Multi-threading) Nə Deməkdir? (Tək fəhlə yoxsa bütöv briqada?)

- Əgər tək işləsən, bir xəbəri açıb oxumaq 1 saniyə çəksə, 100,000 xəbər üçün **28 saat fasiləsiz işləməlisən**.
- Amma sən işə **6 fəhlə (6 worker)** çağırsan:
  - 1-ci fəhlə 1-ci xəbəri açır,
  - 2-ci fəhlə 2-ci xəbəri açır,
  - 3-cü fəhlə 3-cü xəbəri açır...
Və iş **6 dəfə daha tez bitir**.
Bizim qurduğumuz sistemdə də eyni anda 5-6 paralel xətt işləyir və saytı zədələmədən saniyədə 8-10 xəbər toplayır.

---

## 7. GƏLƏCƏKDƏ SƏN NƏ EDƏCƏKSƏN? (Çox Asan Təlimat)

Gələcəkdə sən özün başqa bir saytı scrape etmək istəsən, çətin kodlar yazmağa ehtiyac yoxdur. Sadəcə bu 4 sadə addımı izləyəcəksən:

### Addım 1: Saytın linkini seç
Məsələn, filan xəbər saytını və ya elan saytını götürürsən.

### Addım 2: Brauzerdə sağ düyməni sıxıb "İnspect" (Kodu yoxla) et
Xəbərin başlığının üstündə siçanın sağ düyməsini vurursan -> "İnspect" seçirsən. Görəcəksən ki, başlığın yanında `<h1>` və ya `class="title"` yazılıb. Deməli, robotumuza həmin adı verəcəyik.

### Addım 3: Süni intellektə (mənə) sadə dildə de:
*"Mən filan saytdan məhsulların adını və qiymətini çəkmək istəyirəm. Saytın linki budur. Mənə Report.az-da qurduğumuz kimi sadə və UTF-8 kodlaşdırmalı bir skript yaz."*

### Addım 4: Düyməni sıx və işə sal
Mən sənə hazır, təmiz kodu verəcəyəm. Sən sadəcə terminalda `python fayl_adi.py` yazacaqsan və gözünün qabağında Excel faylı (`.csv`) yaranacaq!

---

## 8. SƏNİN ÜÇÜN ƏSAS KOMANDALAR (Yaddaş vərəqi)

Hazırda Report.az layihəsində istifadə edə biləcəyin ən vacib komandalar:

| Komanda | Nə edir? |
| :--- | :--- |
| `python main.py --mode incremental` | Saytda çıxan ən son xəbərləri dərhal gətirir və Excel faylını təzələyir. |
| `python main.py --mode stats` | Bazada neçə xəbər olduğunu, ən köhnə və ən təzə tarixi göstərir. |
| `python main.py --mode validate` | Xəbərlərdə çatışmayan nəsə olub-olmadığını yoxlayır. |
| `python main.py --mode export` | Bütün xəbərləri yenidən Excel (`articles.csv`) və JSON formatına çıxarır. |

---

### Yekun Söz

Gördüyün kimi, Web Scraping heç də qorxulu və qarışıq bir şey deyil. Bu, sadəcə olaraq **sənin əllə saatlarla edəcəyin kopyala-yapışdır işini proqrama həvalə etməkdir**.

İstədiyin vaxt mənə: *"Gəl indi filan saytdan məlumat çəkək"* deyə bilərsən, addım-addım birlikdə edərik!
