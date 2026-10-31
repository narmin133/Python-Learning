"""Quick parser test"""
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import requests
from article_parser import parse_article

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
}

test_url = 'https://report.az/milli-meclis/azerbaycanda-gomruk-orqanlarinin-vezifeli-sexslerinin-basqa-ise-kecirilmesi-hallari-deyisdirilir'

print(f"Testing parser with: {test_url}\n")

r = requests.get(test_url, headers=HEADERS, timeout=20)
print(f"HTTP Status: {r.status_code}")

article = parse_article(test_url, r.text)

print(f"\n=== PARSED ARTICLE ===")
print(f"Status:       {article.status}")
print(f"Title:        {article.title}")
print(f"Language:     {article.language}")
print(f"Category:     {article.category}")
print(f"Subcategory:  {article.subcategory}")
print(f"Author:       {article.author}")
print(f"Published:    {article.published_at}")
print(f"Published raw: {article.published_at_raw}")
print(f"Updated:      {article.updated_at}")
print(f"Source:       {article.source}")
print(f"Canonical:    {article.canonical_url}")
print(f"Main image:   {article.main_image_url}")
print(f"Images count: {len(article.images)}")
print(f"Videos count: {len(article.videos)}")
print(f"Tags:         {article.tags}")
print(f"Content length: {article.content_length} chars")
print(f"Incomplete:   {article.is_incomplete}")
print(f"OG title:     {article.og_title}")
print(f"Meta desc:    {article.meta_description}")
print(f"\nContent preview (first 500 chars):")
print(article.content[:500] if article.content else 'EMPTY')

