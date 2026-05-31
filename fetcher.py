
import json
import html as html_lib
import random
import time

from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests

from config import BLOCK_THRESHOLD
from logger import logger
from normalize import normalize_params, normalize_published_at
from proxy import rotate_ip


# Авито блокирует запросы по TLS fingerprint — стандартный Python-запрос отличается
# от браузера ещё на уровне TCP-рукопожатия, до передачи любых данных.
# curl_cffi имитирует fingerprint реального Chrome, чередуем версии для разнообразия.
_IMPERSONATE    = ["chrome120", "chrome124", "chrome131"]
_block_attempts = 0  # счётчик блокировок подряд, сбрасывается при успехе


def fetch_html(url, proxy_url=None):
    global _block_attempts
    try:
        # Новая сессия на каждый запрос — уникальный fingerprint при каждом обращении
        session = cffi_requests.Session(impersonate=random.choice(_IMPERSONATE))
        kwargs  = {"timeout": 30, "allow_redirects": True}
        if proxy_url:
            kwargs["proxy"] = proxy_url
        r = session.get(url, **kwargs)
        if r.status_code == 200:
            # Авито отдаёт капчу/заглушку с кодом 200, а не 403 — проверяем текст
            if "Доступ ограничен" in r.text:
                _block_attempts += 1
                logger.warning(f"Доступ ограничен (подряд: {_block_attempts}): {url}")
                if _block_attempts >= BLOCK_THRESHOLD:
                    logger.warning("Достигнут лимит — ротация IP")
                    rotate_ip()
                    _block_attempts = 0
                    time.sleep(60)
                else:
                    time.sleep(random.uniform(10, 20))
                return None
            _block_attempts = 0
            return r.text
        if r.status_code in (403, 429):
            _block_attempts += 1
            logger.warning(f"HTTP {r.status_code} (подряд: {_block_attempts}): {url}")
            if _block_attempts >= BLOCK_THRESHOLD:
                logger.warning("Достигнут лимит — ротация IP")
                rotate_ip()
                _block_attempts = 0
                time.sleep(60)
            else:
                time.sleep(random.uniform(10, 20))
        else:
            logger.warning(f"HTTP {r.status_code}: {url}")
        return None
    except Exception as e:
        logger.error(f"fetch_html {url}: {e}")
        return None


def _extract_page_json(html):
    # Авито встраивает полное состояние страницы в JSON внутри тега <script type="mime/invalid">.
    # type="mime/invalid" — намеренно невалидный MIME, чтобы браузер не исполнял скрипт.
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.select("script[type='mime/invalid'][data-mfe-state='true']"):
        raw = script.string or ""
        if "sandbox" in raw:
            # Скрипты с "sandbox" — служебные iframe-конфиги, не данные каталога
            continue
        data = None
        try:
            data = json.loads(raw)
        except ValueError:
            try:
                # Иногда Авито HTML-экранирует JSON внутри скрипта (&quot; вместо ")
                data = json.loads(html_lib.unescape(raw))
            except ValueError:
                continue
        # Нужный скрипт содержит i18n.hasMessages — отличаем его от остальных
        if data and data.get("i18n", {}).get("hasMessages"):
            return data.get("state", {}).get("data", {})
    return {}


def collect_links(html):
    # Сначала пробуем JSON — надёжнее и не зависит от вёрстки
    data  = _extract_page_json(html)
    items = (data.get("catalog") or {}).get("items") or []
    links = []
    for item in items:
        path = item.get("urlPath")
        if path:
            url = ("https://www.avito.ru" + path) if path.startswith("/") else path
            links.append(url.split("?")[0])  # убираем UTM-метки и параметры
    if not links:
        # Fallback: парсим HTML напрямую, если JSON не нашёлся (смена вёрстки)
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.select("a[data-marker='item-title']"):
            href = a.get("href", "")
            if href:
                url = ("https://www.avito.ru" + href) if href.startswith("/") else href
                links.append(url.split("?")[0])
    return links


def parse_listing(html, url):
    soup = BeautifulSoup(html, "html.parser")

    def text(selector):
        el = soup.select_one(selector)
        return el.get_text(strip=True) if el else None

    result          = {"url": url}
    result["title"] = text("h1[data-marker='item-view/title-info']")

    # Цена лежит в атрибуте content, а не в тексте — там чистое число без пробелов
    price_el        = soup.select_one("span[itemprop='price'][data-marker='item-view/item-price']")
    _price          = price_el.get("content") if price_el else None
    result["price"] = int(_price) if _price and _price.isdigit() else None

    # Параметры квартиры — список пар «лейбл: значение».
    # Значение вырезаем срезом по длине лейбла, а не через replace() —
    # иначе совпадение подстроки в значении обрежет его.
    params = {}
    for li in soup.select("div[data-marker='item-view/item-params'] li"):
        label_el = li.select_one("span:first-child")
        if label_el:
            label_text = label_el.get_text(strip=True)
            label      = label_text.rstrip(":")
            value      = li.get_text(strip=True)[len(label_text):].strip()
            if label and value:
                params[label] = value
    result.update(normalize_params(params))

    address_el        = soup.select_one("div[itemprop='address'] span")
    result["address"] = address_el.get_text(strip=True) if address_el else None

    # Станции метро определяем по цветным кружкам линий (i с inline background-color),
    # название берём из соседнего span
    metro      = []
    addr_block = soup.select_one("div[itemprop='address']")
    if addr_block:
        for indicator in addr_block.select("i[style*='background-color']"):
            name_span = indicator.parent.find_next_sibling("span")
            if name_span:
                name = name_span.get_text(strip=True)
                if name:
                    metro.append(name)
    result["metro"] = metro or None

    desc_el               = soup.select_one("div[data-marker='item-view/item-description']")
    result["description"] = desc_el.get_text(separator="\n", strip=True) if desc_el else None
    result["published_at"] = normalize_published_at(text("span[data-marker='item-view/item-date']"))

    # item_id: берём из страницы, fallback — последний сегмент URL после "_"
    raw_id            = text("span[data-marker='item-view/item-id']")
    result["item_id"] = raw_id or url.rstrip("/").split("_")[-1]

    # Координаты и название города из window.__staticRouterHydrationData
    import re as _re
    m = _re.search(r'window\.__staticRouterHydrationData\s*=\s*JSON\.parse\("(.+?)"\);', html, _re.DOTALL)
    if m:
        try:
            # Двухшаговый парсинг: JSON.parse("...") — внутри экранированная JSON-строка.
            # json.loads('"' + raw + '"') сначала раскрывает escaping, потом парсим сам JSON.
            json_str = json.loads('"' + m.group(1) + '"')
            rdata    = json.loads(json_str)
            item = (
                rdata.get("loaderData", {})
                     .get("catalog-or-main-or-item", {})
                     .get("buyerItem", {})
                     .get("item", {})
            )
            coords = item.get("geo", {}).get("coords", {})
            result["lat"] = coords.get("lat")
            result["lon"] = coords.get("lng")
            # Название города берём у Авито — не доверяем нашему словарю
            city_name = item.get("location", {}).get("name")
            if city_name:
                result["city"] = city_name
        except Exception:
            pass

    return result
