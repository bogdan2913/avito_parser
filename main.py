import random
import time

from config import CITY_CATALOG_URLS, ROTATE_INTERVAL
from db import Database, save
from crawler import collect_all_links, parse_with_retry
from proxy import get_proxy_url, rotate_ip
from notifer import notify
from logger import logger

proxy_url= get_proxy_url()
last_rotate = time.time()

cities     = list(CITY_CATALOG_URLS.items())
total      = len(cities)
city_times = []

with Database() as db:
    for city_idx, (city_name, catalog_url) in enumerate(cities, 1):
        city_start = time.time()
        logger.info(f"=== {city_name} ===")
        links = collect_all_links(proxy_url, catalog_url)
        logger.info(f"Итого ссылок: {len(links)}")

        ok                 = 0
        quality_buckets    = {"0%": 0, "1-49%": 0, "50-99%": 0, "100%": 0}
        failed             = []
        consecutive_errors = 0
        rotated_on_errors  = False

        for i, url in enumerate(links, 1):
            if time.time() - last_rotate > ROTATE_INTERVAL:
                logger.info("Проактивная смена IP...")
                rotate_ip()
                last_rotate = time.time()

            data = parse_with_retry(proxy_url, url)

            time.sleep(random.uniform(1.0, 2.0))

            if data is None:
                failed.append(url)
                consecutive_errors += 1
                if consecutive_errors >= 5:
                    if rotated_on_errors:
                        logger.error("После ротации IP — опять 5 ошибок подряд. Останавливаемся.")
                        break
                    logger.error("5 ошибок подряд — меняем IP и продолжаем")
                    rotate_ip()
                    consecutive_errors = 0
                    rotated_on_errors  = True
                continue

            consecutive_errors = 0
            data["source"] = "avito"
            # Город берём из JSON Авито (parse_listing); наш ключ — только fallback
            if not data.get("city"):
                data["city"] = city_name

            quality_fields = ["title", "price", "address", "rooms", "floor",
                              "area_total", "house_type", "year_built"]
            fill_pct = sum(1 for f in quality_fields if data.get(f) is not None) / len(quality_fields) * 100

            if fill_pct == 0:
                quality_buckets["0%"] += 1
            elif fill_pct < 50:
                quality_buckets["1-49%"] += 1
            elif fill_pct < 100:
                quality_buckets["50-99%"] += 1
            else:
                quality_buckets["100%"] += 1

            if fill_pct == 0:
                logger.warning(f"[{i}/{len(links)}] Качество 0%, пропускаем: {url}")
                failed.append(url)
                continue

            if fill_pct < 50:
                logger.warning(f"[{i}/{len(links)}] Качество {fill_pct:.0f}%: {url}")

            try:
                save(db, data)
                ok += 1
                logger.info(f"[{i}/{len(links)}] OK: {url}")
            except Exception as e:
                failed.append(url)
                logger.error(f"[{i}/{len(links)}] Ошибка сохранения: {e}")

        if failed:
            logger.warning(f"Не удалось спарсить ({len(failed)}):")
            for u in failed:
                logger.warning(f"  {u}")

        logger.info(
            f"\n=== Итог {city_name} ===\n"
            f"Всего ссылок:    {len(links)}\n"
            f"Успешно:         {ok}\n"
            f"Ошибок:          {len(failed)}\n"
            f"Качество 0%:     {quality_buckets['0%']}\n"
            f"Качество 1-49%:  {quality_buckets['1-49%']}\n"
            f"Качество 50-99%: {quality_buckets['50-99%']}\n"
            f"Качество 100%:   {quality_buckets['100%']}"
        )

        city_times.append(time.time() - city_start)
        remaining  = total - city_idx
        avg        = sum(city_times) / len(city_times)
        eta_sec    = avg * remaining
        if eta_sec >= 3600:
            eta_str = f"{int(eta_sec // 3600)}ч {int(eta_sec % 3600 // 60)}м"
        elif eta_sec >= 60:
            eta_str = f"{int(eta_sec // 60)}м"
        else:
            eta_str = "меньше минуты"

        notify(
            f"Авито / {city_name} [{city_idx}/{total}]\n"
            f"Всего ссылок: {len(links)}\n"
            f"Успешно: {ok}\n"
            f"Ошибок: {len(failed)}\n"
            f"Осталось: {remaining} {'город' if remaining == 1 else 'городов'}"
            + (f" (~{eta_str})" if remaining > 0 else " — всё готово ✅")
        )

logger.info("Парсинг завершён")