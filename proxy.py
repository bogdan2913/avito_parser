import requests
from urllib.parse import quote
from config import PROXY_SERVER, PROXY_USERNAME, PROXY_PASSWORD, PROXY_ROTATE_URL


def get_proxy_url():
    if not PROXY_SERVER:
        return None
    server = PROXY_SERVER
    for prefix in ("https://", "http://"):
        if server.startswith(prefix):
            server = server[len(prefix):]
            break
    if PROXY_USERNAME:
        p = quote(PROXY_PASSWORD, safe="")
        return f"http://{PROXY_USERNAME}:{p}@{server}"
    return f"http://{server}"


def rotate_ip():
    if not PROXY_ROTATE_URL:
        return False
    try:
        r = requests.get(PROXY_ROTATE_URL, timeout=10)
        return r.status_code == 200
    except Exception:
        return False