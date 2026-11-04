import requests
from bs4 import BeautifulSoup
import csv


print("Trend.az - XƏBƏRLƏRİN TOPLANMASI")



headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9,ru;q=0.8,en-GB;q=0.7,az;q=0.6"
}

session = requests.Session()
session.headers.update(headers)

main_page = session.get("https://az.trend.az/", timeout=15)
main_page.encoding = 'utf-8'

soup_main = BeautifulSoup(main_page.text, 'lxml')

news_urls = []
for a in soup_main.find_all('a', href=True):
    href = a['href']
    if href.startswith('https://az.trend.az/') and any(char.isdigit() for char in href.split('-')[-1]):
        if href not in news_urls and 'locale=' not in href:
            news_urls.append(href)

print(f"Tapılan xəbər sayı: {len(news_urls)}")

results = []
for i, url in enumerate(news_urls[:5], 1):
 try:
    r= session.get(url, timeout=10)
    r.encoding = 'utf-8'
   
    soup = BeautifulSoup(r.text, 'lxml')
    h4 = soup.find('h4')  
    page_title = soup.find('title')
    title = page_title.get_text(strip=True).replace(' - Trend.Az', '') if page_title else "Başlıq tapılmadı"
    
    results.append({"title": title, "url": url})
    print(f"{i}. {title}")
    print(f"   {url}")

 except requests.RequestException as e:
    print(f"{i}. Səhifəni yükləmək mümkün olmadı: {e}")


csv_filename = "trend_az_news.csv"

with open(csv_filename,'w', newline='', encoding='utf-8') as csv_file:
    writer = csv.writer(csv_file)
    writer.writerow(["Başlıq", "Link"])
    for result in results:
        writer.writerow([result["title"], result["url"]])