import random
import time

from config import MAX_PAGES_PER_SESSION
from fetcher import fetch_html, collect_links, parse_listing
from logger import logger



def collect_all_links(proxy_url, base_url):
    seen      = set()
    all_links = []
    sep       = "&" if "?" in base_url else "?"

    for page_num in range(1, MAX_PAGES_PER_SESSION + 1):
        url  = base_url if page_num == 1 else f"{base_url}{sep}p={page_num}"
        logger.info(f"Каталог стр. {page_num}: {url}")

        html = fetch_html(url, proxy_url)
        if not html:
            logger.error(f"Стр. {page_num}: не удалось загрузить")
            break

        links = collect_links(html)
        if not links:
            logger.info(f"Стр. {page_num}: объявлений нет, выходим")
            break

        # Фильтруем: оставляем только ссылки, принадлежащие запрошенному городу.
        # Если Авито не нашёл объявлений и подставил другой город — отбрасываем весь результат.
        city_slug = base_url.split("avito.ru/")[1].split("/")[0]
        links = [l for l in links if f"/{city_slug}/" in l]
        if not links:
            logger.info(f"Стр. {page_num}: объявления не из {city_slug!r}, пропускаем город")
            break

        new_links = [l for l in links if l not in seen]
        seen.update(new_links)
        all_links.extend(new_links)
        logger.info(f"Стр. {page_num}: +{len(new_links)} новых (итого: {len(all_links)})")
        time.sleep(random.uniform(1.0, 2.5))

    return all_links


def parse_with_retry(proxy_url, url, attempts=3):
    for attempt in range(1, attempts + 1):
        try:
            html = fetch_html(url, proxy_url)
            if html:
                data = parse_listing(html, url)
                if data is not None:
                    return data
        except Exception:
            logger.exception(f"Попытка {attempt}/{attempts}: {url}")
        logger.warning(f"Попытка {attempt}/{attempts} не удалась: {url}")
        if attempt < attempts:
            time.sleep(5 * attempt)
    return None