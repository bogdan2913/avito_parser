# Генератор фильтр-URL для Авито.
# Принимает готовую ссылку из конфига, возвращает словарь с разбивкой.

import base64
import json


def split_by_rooms(city, url):
    rooms = {
        "студия": ("studii", b"\xCA\x08\xFE\x58"),
        "1к": ("1-komnatnye", b"\xCA\x08\x80\x59"),
        "2к": ("2-komnatnye", b"\xCA\x08\x82\x59"),
        "3к": ("3-komnatnye", b"\xCA\x08\x84\x59"),
        "4к": ("4-komnatnye", b"\xCA\x08\x86\x59"),
        "5к": ("5-komnatnye", b"\xCA\x08\x88\x59"),
        "6к": ("6-komnatnye", b"\xCA\x08\x8A\x59"),
        "7к": ("7-komnatnye", b"\xCA\x08\x8C\x59"),
        "8к": ("8-komnatnye", b"\xCA\x08\x8E\x59"),
        "9к": ("9-komnatnye", b"\xCA\x08\x90\x59"),
        "10к+": ("10-komnatnyh-i-bolee", b"\xCA\x08\x92\x59"),
        "своб": ("svobodnaya_planirovka", b"\xCA\x08\xFC\xCF\x32"),
    }

    slug = url.split("avito.ru/")[1].split("/")[0]
    hdr  = b"\x01\x28\x01\x02\x02\x03\x02\x44\x92\x03\xC6\x10\xE6\x07\x8C\x52"

    return {
        f"{city} ({room})":
            f"https://www.avito.ru/{slug}/kvartiry/prodam/{path}/vtorichka-"
            f"{base64.urlsafe_b64encode(hdr + code).rstrip(b'=').decode()}"
            f"?localPriority=0"
        for room, (path, code) in rooms.items()
    }


def split_by_price(city, url, breakpoints=None):
    points = breakpoints or [
        3_000_000, 5_000_000, 7_000_000, 9_000_000,
        *range(10_000_000, 51_000_000, 1_000_000),
        70_000_000, 100_000_000, 200_000_000,
        300_000_000, 500_000_000, 1_000_000_000,
        10_000_000_000,
    ]

    slug = url.split("avito.ru/")[1].split("/")[0]

    base = base64.urlsafe_b64encode(
        b"\x01\x28\x01\x02\x02\x02\x02\x44\x92\x03\xC6\x10\xE6\x07\x8C\x52"
    ).rstrip(b"=").decode()

    result = {}

    for frm, to in zip([0] + points, points + [0]):
        payload = json.dumps(
            {"from": frm, "to": to},
            separators=(",", ":"),
            ensure_ascii=True
        ).encode()

        filt = base64.urlsafe_b64encode(
            b"\x01\x28\x01\x02\x01\x02\x02\x44\x92\x03\xC6\x10\xE6\x07\x8C\x52"
            + b"\x01\x45\xC6\x9A\x0C"
            + bytes([len(payload)])
            + payload
        ).rstrip(b"=").decode()

        def fmt(v):
            if v == 0:
                return "0"
            if v % 1_000_000_000 == 0:
                return f"{v // 1_000_000_000}млрд"
            if v % 1_000_000 == 0:
                return f"{v // 1_000_000}М"
            return str(v)

        label = f"{fmt(frm)}+" if to == 0 else f"{fmt(frm)}-{fmt(to)}"

        result[f"{city} ({label})"] = (
            f"https://www.avito.ru/{slug}/kvartiry/prodam/"
            f"vtorichka-{base}?localPriority=0&f={filt}"
        )

    return result




# По ценовым сегментам 
for k, v in split_by_price(
    "Химки",
    "https://www.avito.ru/himki/kvartiry/prodam/vtorichka-ASgBAgICAkSSA8YQ5geMUg"
).items():
    print(f'    "{k}": "{v}",')



## По комнатам 
# for k, v in split_by_rooms(
#     "Москва",
#     "https://www.avito.ru/moskva/kvartiry/prodam/vtorichka-ASgBAgICAkSSA8YQ5geMUg?localPriority=0"
# ).items():
#     print(f'    "{k}": "{v}",')