import requests
import re
import xml.etree.ElementTree as ET

HEADERS = {'User-Agent': 'Mozilla/5.0 Chrome/120.0.0.0 Safari/537.36'}

r = requests.get('https://report.az/sitemap.xml', headers=HEADERS, timeout=20)
content = r.text

content_clean = re.sub(r' xmlns(?::[a-zA-Z]+)?="[^"]*"', '', content)
root = ET.fromstring(content_clean)

sitemaps = []
for sm in root.findall('.//sitemap'):
    loc = sm.find('loc')
    lastmod = sm.find('lastmod')
    if loc is not None:
        sitemaps.append((loc.text.strip(), lastmod.text.strip() if lastmod is not None else ''))

print(f'Total sitemaps in index: {len(sitemaps)}')
for sm, lm in sitemaps:
    print(f'  {sm}  [{lm[:10]}]')

# Check news-sitemap.xml
r2 = requests.get('https://report.az/news-sitemap.xml', headers=HEADERS, timeout=20)
print(f'\nnews-sitemap.xml status: {r2.status_code}')
if r2.status_code == 200:
    print(r2.text[:500])

