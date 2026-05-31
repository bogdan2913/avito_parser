import re
from datetime import datetime, timedelta


_MONTHS = {
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4,
    "мая": 5, "июня": 6, "июля": 7, "августа": 8,
    "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
}


def normalize_published_at(text):
    if not text:
        return None
    text = text.strip().lower()
    now = datetime.now()
    time_match = re.search(r"(\d{1,2}):(\d{2})", text)
    hour   = int(time_match.group(1)) if time_match else 0
    minute = int(time_match.group(2)) if time_match else 0
    if "сегодня" in text:
        date = now.date()
    elif "вчера" in text:
        date = (now - timedelta(days=1)).date()
    elif "позавчера" in text:
        date = (now - timedelta(days=2)).date()
    else:
        m = re.search(r"(\d{1,2})\s+(\w+)(?:\s+(\d{4}))?", text)
        if not m:
            return None
        day   = int(m.group(1))
        month = _MONTHS.get(m.group(2))
        if not month:
            return None
        if m.group(3):
            year = int(m.group(3))
        elif month > now.month:
            year = now.year - 1  # «5 декабря» в мае → прошлый год
        else:
            year = now.year
        date = datetime(year, month, day).date()
    return datetime(date.year, date.month, date.day, hour, minute).strftime("%Y-%m-%d %H:%M")


def normalize_params(params):
    def to_float(s):
        if not s:
            return None
        match = re.search(r'[\d]+[,.]?[\d]*', s.replace('\xa0', ''))
        return float(match.group().replace(',', '.')) if match else None

    def to_int(s):
        if not s:
            return None
        match = re.search(r'\d+', s.replace('\xa0', ''))
        return int(match.group()) if match else None

    def to_rooms(s):
        if not s:
            return None
        s = s.lower()
        if 'студия' in s:
            return 0
        if 'свободная' in s:
            return -1
        match = re.search(r'\d+', s)
        return int(match.group()) if match else None

    def contains(key, word):
        val = params.get(key, "")
        return word.lower() in val.lower() if val else False

    balcony_loggia = params.get("Балкон или лоджия", "").lower()
    extra          = params.get("Дополнительно", "").lower()
    in_building    = params.get("В доме", "").lower()

    return {
        "property_type":      params.get("Тип жилья"),
        "rooms":              to_rooms(params.get("Количество комнат")),
        "room_type":          params.get("Тип комнат"),
        "floor":              to_int(params.get("Этаж")),
        "area_total":         to_float(params.get("Общая площадь")),
        "area_living":        to_float(params.get("Жилая площадь")),
        "area_kitchen":       to_float(params.get("Площадь кухни")),
        "ceiling_height":     to_float(params.get("Высота потолков")),
        "renovation":         params.get("Ремонт"),
        "bathroom":           params.get("Санузел"),
        "windows":            params.get("Окна"),
        "furniture":          params.get("Мебель"),
        "appliances":         params.get("Техника"),
        "balcony":            "балкон" in balcony_loggia,
        "loggia":             "лоджия" in balcony_loggia,
        "wardrobe":           "гардеробная" in extra,
        "panoramic_windows":  "панорамные окна" in extra,
        "warm_floor":         "тёплый пол" in extra,
        "house_type":         params.get("Тип дома"),
        "total_floors":       to_int(params.get("Этажей в доме")),
        "year_built":         to_int(params.get("Год постройки")),
        "passenger_elevator": to_int(params.get("Пассажирский лифт")),
        "cargo_elevator":     to_int(params.get("Грузовой лифт")),
        "yard":               params.get("Двор"),
        "parking":            params.get("Парковка"),
        "concierge":          "консьерж" in in_building,
        "garbage_chute":      "мусоропровод" in in_building,
        "gas":                "газ" in in_building,
        "demolition_planned": contains("Запланирован снос", "да"),
        "sale_method":        params.get("Способ продажи"),
        "sale_conditions":    params.get("Условия продажи"),
        "developer":          params.get("Застройщик"),
        "sale_type":          params.get("Тип продажи"),
    }