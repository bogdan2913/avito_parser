import os
from dotenv import load_dotenv

load_dotenv()

# База данных PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user@localhost:5432/course_work")

# Telegram-уведомления
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID", "")

# Мобильный прокси
PROXY_SERVER     = os.getenv("PROXY_SERVER", "")
PROXY_USERNAME   = os.getenv("PROXY_USERNAME", "")
PROXY_PASSWORD   = os.getenv("PROXY_PASSWORD", "")
PROXY_ROTATE_URL = os.getenv("PROXY_ROTATE_URL", "")

## гав гав гав


# Города для парсинга и ссылки на каталог Авито
CITY_CATALOG_URLS = {
    
}


MAX_PAGES_PER_SESSION = 50
ROTATE_INTERVAL       = 9 * 60
BLOCK_THRESHOLD       = 3
