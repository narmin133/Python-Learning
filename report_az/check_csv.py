import csv
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('output/articles.csv', 'r', encoding='utf-8-sig', errors='replace') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

print(f"Total rows in CSV: {len(rows)}")
langs = {}
for r in rows:
    l = r.get('language', 'unknown')
    langs[l] = langs.get(l, 0) + 1
print("Languages in CSV:", langs)

print("\nFirst 10 titles in CSV:")
for i, r in enumerate(rows[:10]):
    print(f"{i+1}. [lang={r.get('language')}] {r.get('title')}")

