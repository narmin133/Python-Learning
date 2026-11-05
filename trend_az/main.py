import requests
from bs4 import BeautifulSoup
import csv
import openpyxl 
import re


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
    if href.startswith('https://az.trend.az/') and href.endswith('.html'):
        if href not in news_urls and 'locale=' not in href:
            news_urls.append(href)

print(f"Tapılan xəbər sayı: {len(news_urls)}")

results = []
for i, url in enumerate(news_urls[:50], 1):
 try:
    r= session.get(url, timeout=10)
    r.encoding = 'utf-8'
   
    soup = BeautifulSoup(r.text, 'lxml')
    h4 = soup.find('h4')  
    page_title = soup.find('title')
    title = page_title.get_text(strip=True).replace(' - Trend.Az', '') if page_title else "Başlıq tapılmadı"

    date_tag = soup.find("span", class_="date-time")
    date = date_tag.get_text(strip=True) if date_tag else "Tarix tapılmadı"

    bc = soup.find("ol", class_="breadcrumbs")
    category = bc.find_all("li")[-1].get_text(strip=True) if bc else "Kateqoriya tapılmadı" 

    content_div = soup.find("div", class_="article-content")
    if content_div:
       paragraphs = [p.get_text(strip=True) for p in content_div.find_all("p")]
       content = " ".join(paragraphs)
       content = re.sub(r'\s+', ' ', content).strip() 
    else: 
       content = "Xəbər məzmunu tapılmadı"   
    
    results.append({
       "title": title, "url": url, "date": date, "category": category, "content": content})
   
    print(f"\n{i}. {title}")
    print(f"   Kateqoriya: {category}")
    print(f"   Tarix: {date}")
    print(f"   Link: {url}")

 except requests.RequestException as e:
    print(f"{i}. Səhifəni yükləmək mümkün olmadı: {e}")


from pathlib import Path
CURRENT_DIR = Path(__file__).parent.resolve()
csv_filename = str(CURRENT_DIR / "trend_az_news.csv")

with open(csv_filename,'w', newline='', encoding='utf-8-sig') as csv_file:
    print(f"\n✅ {len(results)} xəbər uğurla '{csv_filename}' faylına yazıldı!")
    writer = csv.writer(csv_file)
    writer.writerow(["Başlıq", "Link", "Tarix", "Kateqoriya", "Məzmun"])
    for result in results:
        writer.writerow([result["title"], result["url"], result["date"], result["category"], result["content"]])

excel_filename = str(CURRENT_DIR / "trend_az_news.xlsx")
wb = openpyxl.Workbook()
ws = wb.active
ws.title = "Trend.az Xəbərlər"
headers_list=["Başlıq", "Link", "Tarix", "Kateqoriya", "Məzmun"]
ws.append(headers_list) 

for result in results:
    ws.append([result["title"], result["url"], result["date"], result["category"], result["content"]])
wb.save(excel_filename)
print(f"✅ Excel fayli hazirlandi:{excel_filename}")