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

# GEMINI API Keys (Comma separated in env variable)
# Example: GEMINI_API_KEY=key1,key2,key3
_keys: list[str] = []
raw_keys = os.getenv("GEMINI_API_KEY", "")
if raw_keys:
    # Split by comma, remove whitespace, and ignore empty strings
    _keys = [k.strip() for k in raw_keys.split(",") if k.strip()]

GEMINI_API_KEYS: list[str] = _keys

# Serper Web Search API
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "").strip()