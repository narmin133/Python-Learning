import json
from datetime import datetime
import requests

base_url = "https://api.metrix.az/api/v2/stats/sites"
types = ["month"]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/157.0.0.0 Safari/537.36",
    "Referer": "https://metrix.az/"
}

for report_type in types:
    url = f"{base_url}?report_type={report_type}"
    response = requests.get(url, headers=headers)
    data = response.json()

    # Məlumatın götürüldüyü dəqiq tarix və saat (məs: 2026-11-17 17:25:30)
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    period_news = []
    for item in data.get("sites", []):
        period_news.append({
            "title": item.get("title") or item.get("domain"),
            "views": item.get("views"),
            "link": item.get("page_url") or f"https://{item.get('domain')}",
            "scraped_at": current_time
        })

    # Hər dövr üçün ayrıca JSON faylı yaradırıq
    filename = f"metrix_sites_{report_type}.json"
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(period_news, file, ensure_ascii=False, indent=4)

    print(f"✅ {filename} faylı uğurla yaradıldı ({len(period_news)} məlumat).")
