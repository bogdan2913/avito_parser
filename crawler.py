import random
import time

from config import MAX_PAGES_PER_SESSION
from fetcher import fetch_html, collect_links, parse_listing
from proxy import rotate_ip
from logger import logger


def collect_all_links(proxy_url, base_url):
    seen      = set()
    all_links = []
    sep       = "&" if "?" in base_url else "?"

    for page_num in range(1, MAX_PAGES_PER_SESSION + 1):
        url  = base_url if page_num == 1 else f"{base_url}{sep}p={page_num}"
        logger.info(f"Каталог стр. {page_num}: {url}")

        html      = None
        final_url = url
        for attempt in range(1, 4):
            html, final_url = fetch_html(url, proxy_url)
            if html:
                break
            logger.warning(f"Каталог стр. {page_num}: попытка {attempt}/3 не удалась, ждём...")
            time.sleep(10 * attempt)
        if not html:
            logger.error(f"Стр. {page_num}: не удалось загрузить после 3 попыток — ротация IP")
            rotate_ip()
            time.sleep(60)
            html, final_url = fetch_html(url, proxy_url)
        if not html:
            logger.error(f"Стр. {page_num}: не удалось загрузить даже после ротации")
            break

        # Авито часто отвечает 302 (канонизация слага города/региона). curl_cffi
        # уже прошёл по редиректу — парсим страницу, на которую попали по факту.
        if final_url.split("?")[0] != url.split("?")[0]:
            logger.info(f"Стр. {page_num}: редирект {url} -> {final_url}")

        links = collect_links(html)
        if not links:
            logger.info(f"Стр. {page_num}: объявлений нет, выходим")
            break

        # Слаг берём из финального URL: после редиректа объявления приходят с
        # каноническим слагом, и фильтр по исходному слагу вырезал бы их все.
        city_slug = final_url.split("avito.ru/")[1].split("/")[0]
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
            html, final_url = fetch_html(url, proxy_url)
            if html:
                # Парсим страницу, на которую реально попали после редиректа
                data = parse_listing(html, final_url)
                if data is not None:
                    return data
        except Exception:
            logger.exception(f"Попытка {attempt}/{attempts}: {url}")
        logger.warning(f"Попытка {attempt}/{attempts} не удалась: {url}")
        if attempt < attempts:
            time.sleep(5 * attempt)
    return None