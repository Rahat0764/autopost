import os

# Facebook
PAGE_ID = os.getenv("PAGE_ID")
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
APP_ID = os.getenv("APP_ID")
APP_SECRET = os.getenv("APP_SECRET")

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_USER_IDS = os.getenv("TELEGRAM_USER_IDS")

# Language
DEFAULT_LANGUAGE = os.getenv("LANGUAGE", "bn").lower()

# GEMINI API Keys (Comma separated from environment variables)
_keys: list[str] = []
raw_keys = os.getenv("GEMINI_API_KEY", "")
if raw_keys:
    _keys = [k.strip() for k in raw_keys.split(",") if k.strip()]

GEMINI_API_KEYS: list[str] = _keys

# Serper Web Search API
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "").strip()