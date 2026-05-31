## модуль для тестирования и сбора ссылок для парсинга

import requests
from bs4 import BeautifulSoup
import json, time

BASE = "https://www.parseronline.ru/baza/avito/"
HEADERS = {"Referer": BASE, "Content-Type": "application/x-www-form-urlencoded"}

session = requests.Session()

# Получаем список регионов с главной страницы
resp = session.get(BASE, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
soup = BeautifulSoup(resp.text, "lxml")

region_select = soup.find("select")
assert region_select, "select не найден на странице"
regions = [
    (o["value"], o.get_text(strip=True))
    for o in region_select.find_all("option")
    if o.get("value")
]
print(f"Регионов: {len(regions)}")

result = {}

for region_id, region_name in regions:
    # Пробуем разные варианты параметра
    for param_name in ["region", "id_parent", "region_id"]:
        try:
            r = session.post(
                BASE + "show_city.php",
                data={param_name: region_id},
                headers=HEADERS,
                timeout=10
            )
            soup2 = BeautifulSoup(r.text, "lxml")
            options = soup2.find_all("option")
            if options:
                cities = [{"id": o.get("value", ""), "name": o.get_text(strip=True)} for o in options if o.get("value")]
                result[region_name] = {"region_id": region_id, "cities": cities}
                print(f"  {region_name}: {len(cities)} городов (param={param_name})")
                break
        except Exception as e:
            print(f"  {region_name} [{param_name}]: {e}")
    else:
        # Ни один параметр не сработал
        print(f"  {region_name}: 0 городов")
        result[region_name] = {"region_id": region_id, "cities": []}

    time.sleep(0.3)

with open("cities_raw.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

total = sum(len(v["cities"]) for v in result.values())
print(f"\nГотово. Регионов: {len(result)}, городов всего: {total}")
print("Сохранено в cities_raw.json")
