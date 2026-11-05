from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import csv

def get_article_links(browser, max_links=5):
    """Əsas səhifədən unikal məqalə linklərini toplayır"""
    url = "https://www.wsj.com/market-data"
    print(f"Əsas səhifə açılır: {url}")
    browser.get(url)
    time.sleep(3)

    # Bütün linkləri axtarırıq
    links = browser.find_elements(By.XPATH, "//a[contains(@href, '/articles/') or contains(@href, '/finance/') or contains(@href, '/economy/')]")
    
    unique_urls = []
    for link in links:
        href = link.get_attribute("href")
        if href and href not in unique_urls and "wsj.com" in href:
            # Şərh və ya profil linklərini kənarlaşdırırıq
            if "#comments" not in href:
                unique_urls.append(href)
        if len(unique_urls) >= max_links:
            break

    return unique_urls

def extract_article_content(browser, url):
    """Verilmiş məqalə linkinə daxil olub tam mətni və başlığı çıxarır"""
    print(f"\nMəqaləyə keçid edilir: {url}")
    browser.get(url)
    time.sleep(2)

    # 1. Başlığı çıxarırıq (h1)
    title = "Başlıq tapılmadı"
    try:
        h1_element = browser.find_element(By.TAG_NAME, "h1")
        title = h1_element.text.strip()
    except NoSuchElementException:
        pass

    # 2. Məqalənin paraqraflarını toplayırıq
    paragraphs = []
    try:
        # WSJ-də məqalə mətni əsasən <article> və ya <section> daxilindəki <p> teqlərində olur
        p_elements = browser.find_elements(By.XPATH, "//article//p | //main//p")
        for p in p_elements:
            text = p.text.strip()
            # Çox qısa bildirişləri və ya reklam yazılarını atırıq
            if len(text) > 30 and not text.startswith("Copyright") and not text.startswith("Dow Jones"):
                paragraphs.append(text)
    except Exception as e:
        print(f"Mətn çıxarılarkən xəta: {e}")

    full_body = "\n\n".join(paragraphs) if paragraphs else "Kontent tapılmadı (Paywall və ya qeydiyyat tələb olunur)"

    return {
        "title": title,
        "url": url,
        "content": full_body
    }

def main():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    browser = webdriver.Chrome(options=options)
    all_articles = []

    try:
        # Neçə məqalənin tam oxunmasını istəyirsinizsə max_links ilə tənzimləyə bilərsiniz
        article_urls = get_article_links(browser, max_links=5)
        print(f"Cəmi {len(article_urls)} məqalə linki tapıldı.")

        for idx, url in enumerate(article_urls, start=1):
            article_data = extract_article_content(browser, url)
            all_articles.append(article_data)

            print(f"[{idx}/{len(article_urls)}] Başlıq: {article_data['title']}")
            print(f"Paraqraf sayı: {len(article_data['content'].splitlines())}")
            print("Kontentdən ilk 200 simvol:")
            print(article_data['content'][:200] + ("..." if len(article_data['content']) > 200 else ""))
            print("-" * 50)
            time.sleep(1)

        # Məlumatları CSV faylına saxlayırıq
        csv_filename = "wsj_articles.csv"
        with open(csv_filename, mode="w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["title", "url", "content"])
            writer.writeheader()
            writer.writerows(all_articles)

        print(f"\nUğurlu! Bütün məqalələr '{csv_filename}' faylına yazıldı.")

    except Exception as e:
        print(f"Ümumi xəta baş verdi: {e}")

    finally:
        print("Brauzer bağlanır...")
        browser.quit()

if __name__ == "__main__":
    main()
