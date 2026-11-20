import json
from datetime import datetime
from pathlib import Path
import sys
import warnings
import requests
import pika

# Pika xəbərdarlıqlarını gizlədirik
warnings.filterwarnings("ignore", category=DeprecationWarning)

CURRENT_DIR = Path(__file__).parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.append(str(CURRENT_DIR))

# ========================================================
# RabbitMQ Konfiqurasiyası (Məxfi config.py faylından oxunur)
# ========================================================
try:
    from config import RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_USER, RABBITMQ_PASS, RABBITMQ_QUEUE
except ImportError:
    RABBITMQ_HOST = "localhost"
    RABBITMQ_PORT = 5672
    RABBITMQ_USER = "guest"
    RABBITMQ_PASS = "guest"
    RABBITMQ_QUEUE = "metrix.az"

def send_to_rabbitmq(items):
    try:
        credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
        parameters = pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            credentials=credentials
        )
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()

        # Növbə (Queue) mövcud deyilsə yaradılır
        channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)

        for item in items:
            channel.basic_publish(
                exchange="",
                routing_key=RABBITMQ_QUEUE,
                body=json.dumps(item, ensure_ascii=False),
                properties=pika.BasicProperties(delivery_mode=2)  # Mesajların itməməsi üçün
            )

        connection.close()
        print(f"🚀 {len(items)} məlumat RabbitMQ '{RABBITMQ_QUEUE}' növbəsinə göndərildi.")
    except Exception as e:
        print(f"⚠️ RabbitMQ-yə göndərilərkən xəta yarandı: {e}")


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

    # Məlumatın götürüldüyü dəqiq tarix və saat
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    period_news = []
    for item in data.get("sites", []):
        period_news.append({
            "title": item.get("title") or item.get("domain"),
            "views": item.get("views"),
            "link": item.get("page_url") or f"https://{item.get('domain')}",
            "period": report_type,
            "nov": "veb-sayt",
            "scraped_at": current_time
        })

    # Hər dövr üçün ayrıca JSON faylı yaradırıq
    filename = CURRENT_DIR / f"metrix_sites_{report_type}.json"
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(period_news, file, ensure_ascii=False, indent=4)

    print(f"✅ {filename.name} faylı uğurla yaradıldı ({len(period_news)} məlumat).")

    # RabbitMQ-yə göndəririk
    send_to_rabbitmq(period_news)
