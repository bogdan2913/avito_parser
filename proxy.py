import time
import requests
from urllib.parse import quote
from config import PROXY_SERVER, PROXY_USERNAME, PROXY_PASSWORD, PROXY_ROTATE_URL

_last_rotate = 0
_MIN_ROTATE_INTERVAL = 60  # секунд между ротациями


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
    global _last_rotate
    if not PROXY_ROTATE_URL:
        return False
    if time.time() - _last_rotate < _MIN_ROTATE_INTERVAL:
        return False
    try:
        r = requests.get(PROXY_ROTATE_URL, timeout=10)
        if r.status_code == 200:
            _last_rotate = time.time()
            return True
        return False
    except Exception:
        return False