import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_USER_IDS

def send_alert(msg):
    for uid in TELEGRAM_USER_IDS:
        uid = uid.strip()
        if not uid:
            continue

        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            data={"chat_id": uid, "text": msg}
        )