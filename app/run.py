import time
import random
import requests
from datetime import datetime

from config import (
    PAGE_ID,
    PAGE_ACCESS_TOKEN,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_USER_IDS,
)
from topics import TOPICS
from ai_generator import generate_post
from image_maker import create_image


# ─────────────────────────────────────────────
# Telegram MarkdownV2 escape helper
# ─────────────────────────────────────────────

def mdv2(text: str) -> str:
    """Telegram MarkdownV2-এ special characters escape করে।"""
    for ch in r"\_*[]()~`>#+-=|{}.!":
        text = text.replace(ch, f"\\{ch}")
    return text


# ─────────────────────────────────────────────
# Facebook
# ─────────────────────────────────────────────

def post_to_facebook(message: str, image_path: str) -> dict:
    url = f"https://graph.facebook.com/{PAGE_ID}/photos"

    with open(image_path, "rb") as img:
        res = requests.post(
            url,
            data={
                "caption": message,
                "access_token": PAGE_ACCESS_TOKEN,
                "published": "true",
            },
            files={"source": img},
        )

    return res.json()


# ─────────────────────────────────────────────
# Telegram
# ─────────────────────────────────────────────

def send_telegram(message: str):
    for user_id in TELEGRAM_USER_IDS.split(","):
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, data={
            "chat_id": user_id.strip(),
            "text": message,
            "parse_mode": "MarkdownV2",
        })


# ─────────────────────────────────────────────
# Main Loop
# ─────────────────────────────────────────────

def run():
    print("🚀 Running...")

    while True:
        topic = random.choice(TOPICS)
        print("📝 Topic:", topic)

        result  = generate_post(topic)
        title   = result["title"]
        content = result["content"]

        print("🏷 Title:", title)

        # Facebook post
        full_message = f"{title}\n\n{content}"
        image_path   = create_image(title)
        fb_res       = post_to_facebook(full_message, image_path)
        print("FB Response:", fb_res)

        # Telegram log
        now     = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        post_id = fb_res.get("post_id", "N/A")

        telegram_msg = (
            "🚀 *New Post Created*\n\n"
            f"📝 Topic: *{mdv2(topic)}*\n"
            f"🏷 Title: *{mdv2(title)}*\n\n"
            f"🕒 Date & Time: {mdv2(now)}\n\n"
            f"📌 Post ID: ||{mdv2(str(post_id))}||\n"
            f"👤 Page ID: ||{mdv2(str(PAGE_ID))}||\n\n"
            f"📄 Preview:\n>{mdv2(content[:200])}\\.\\.\\."
        )

        send_telegram(telegram_msg)

        TIME_IN_MIN = 5

        print(f"⏳ Waiting {TIME_IN_MIN} minutes...")
        time.sleep(TIME_IN_MIN*60)


if __name__ == "__main__":
    run()