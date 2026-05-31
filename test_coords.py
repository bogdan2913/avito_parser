## тест координат через parse_listing

import sys
sys.path.insert(0, '.')

from fetcher import fetch_html, parse_listing
from proxy import get_proxy_url

URL = "https://www.avito.ru/saratov/kvartiry/1-k._kvartira_43_m_1125_et._8056868484"

proxy_url = get_proxy_url()
print(f"Fetching: {URL}")
html = fetch_html(URL, proxy_url)

if not html:
    print("Не удалось получить HTML")
    exit(1)

result = parse_listing(html, URL)

print(f"\nlat: {result.get('lat')}")
print(f"lng: {result.get('lng')}")
print(f"address: {result.get('address')}")
print(f"title: {result.get('title')}")
print(f"price: {result.get('price')}")
