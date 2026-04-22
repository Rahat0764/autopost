import os
import time
import random
import threading
import requests
from datetime import datetime
from flask import Flask

import db
from config import (
    PAGE_ID, PAGE_ACCESS_TOKEN,
    TELEGRAM_BOT_TOKEN, TELEGRAM_USER_IDS,
    DEFAULT_LANGUAGE,
)
from topics import TOPICS
from ai_generator import generate_post
import ai_generator
from image_maker import create_image

# Web server setup for Render
app = Flask(__name__)

@app.route('/')
def home():
    return "AutoPost Bot is running 24/7!"

POST_TIMES = ["09:00", "14:00", "21:00"]
MAX_FB_RETRIES = 2

_state = {
    "language": DEFAULT_LANGUAGE,
    "paused": False,
    "last_update": 0,
    "force_topic": None,
}
_posted_today: set = set()
_topic_queue:  list = []

def _lang() -> str:
    return _state["language"]

def next_topic() -> str:
    global _topic_queue
    if not _topic_queue:
        _topic_queue = TOPICS.copy()
        random.shuffle(_topic_queue)
        db.info("Topic queue refreshed", {"total": len(TOPICS)})
    recent = set(db.get_recent_topics(10))
    for _ in range(len(_topic_queue)):
        if _topic_queue[-1] not in recent:
            return _topic_queue.pop()
        _topic_queue.insert(0, _topic_queue.pop())
    return _topic_queue.pop()

def notify(msg: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_USER_IDS:
        return
    uids = [u.strip() for u in str(TELEGRAM_USER_IDS).split(",") if u.strip()]
    for uid in uids:
        try:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": uid, "text": msg}
            )
        except Exception as e:
            db.error("Telegram notification failed", {"error": str(e)})

def post_to_facebook(text: str, img_path: str = None) -> str:
    if not PAGE_ID or not PAGE_ACCESS_TOKEN:
        raise ValueError("Facebook credentials missing")
    
    url = f"https://graph.facebook.com/v18.0/{PAGE_ID}/photos"
    data = {"message": text, "access_token": PAGE_ACCESS_TOKEN}
    
    for attempt in range(1, MAX_FB_RETRIES + 1):
        try:
            with open(img_path, "rb") as f:
                files = {"file": f}
                r = requests.post(url, data=data, files=files, timeout=30)
            res = r.json()
            if "id" in res:
                return res["id"]
            if attempt == MAX_FB_RETRIES:
                raise RuntimeError(f"FB Error: {res}")
            time.sleep(5)
        except Exception as e:
            if attempt == MAX_FB_RETRIES:
                raise e
            time.sleep(5)
    return None

def do_post(forced_topic: str = None):
    topic = forced_topic or next_topic()
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Processing: {topic}")
    try:
        post_data = generate_post(topic, _lang())
        img_path  = create_image(post_data["title"], _lang(), topic)
        fb_id     = post_to_facebook(post_data["content"], img_path)

        with db._conn() as c:
            c.execute(
                "INSERT INTO posts (topic, title, content, language, fb_post_id, created_at) VALUES (?,?,?,?,?,?)",
                (topic, post_data["title"], post_data["content"], _lang(), fb_id, datetime.now().isoformat())
            )
        
        db.mark_title_used(post_data["title_hash"], topic)
        db.add_token_usage(post_data.get("api_key_idx", 0), post_data["model"], post_data["tokens"])

        notify(
            f"✅ Posted Successfully!\n"
            f"Topic: {topic}\n"
            f"Title: {post_data['title']}\n"
            f"Tokens: {post_data['tokens']}\n"
            f"Link: https://facebook.com/{PAGE_ID}_{fb_id}"
        )
        print("Success!")
    except Exception as e:
        db.error("Post processing failed", {"topic": topic, "error": str(e)})
        notify(f"❌ Post Failed!\nTopic: {topic}\nError: {str(e)}")

# Long polling function for Telegram Bot commands
def bot_polling():
    if not TELEGRAM_BOT_TOKEN:
        print("Telegram Bot Token is missing. Polling disabled.")
        return
        
    last_update_id = 0
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    
    print("📡 Telegram polling started...")
    while True:
        try:
            response = requests.get(f"{url}?offset={last_update_id}&timeout=30", timeout=40)
            data = response.json()
            
            if data.get("ok"):
                for result in data["result"]:
                    last_update_id = result["update_id"] + 1
                    message = result.get("message")
                    
                    if not message or "text" not in message:
                        continue
                        
                    chat_id = str(message["chat"]["id"])
                    text = message["text"].strip()
                    
                    # Security check
                    allowed_users = [u.strip() for u in str(TELEGRAM_USER_IDS).split(",") if u.strip()]
                    if chat_id not in allowed_users:
                        continue

                    # Command routing
                    if text == "/help":
                        reply = "Commands:\n/post - Force random post\n/post <topic> - Force specific topic\n/pause - Pause auto-post\n/resume - Resume auto-post\n/status - Check status"
                        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": reply})
                        
                    elif text.startswith("/post"):
                        parts = text.split(" ", 1)
                        if len(parts) > 1:
                            topic = parts[1]
                            _state["force_topic"] = topic
                            reply = f"⏳ Forcing post for topic: {topic}"
                        else:
                            _state["force_topic"] = "__auto__"
                            reply = "⏳ Forcing a random post now..."
                        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": reply})

                    elif text == "/pause":
                        _state["paused"] = True
                        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": "⏸️ Bot paused."})

                    elif text == "/resume":
                        _state["paused"] = False
                        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": "▶️ Bot resumed."})

                    elif text == "/status":
                        status = "Paused ⏸️" if _state["paused"] else "Running ▶️"
                        stats = db.get_stats_summary()
                        reply = f"Status: {status}\nLanguage: {_lang()}\nTotal Posts: {stats['total_posts']}\nToday Tokens: {stats['tokens_today']}"
                        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": reply})
                        
        except Exception as e:
            # Silently ignore connection errors during polling to prevent crash
            time.sleep(5)
            
        time.sleep(1)

def bot_loop():
    print("🚀 AutoPost bot logic started...")
    db.init_db()
    stats = db.get_stats_summary()
    
    # Run telegram polling in background
    threading.Thread(target=bot_polling, daemon=True).start()
    
    notify(f"🚀 AutoPost Server Started!\nLanguage: {_lang()}\nTotal Posts: {stats['total_posts']}\nSend /help for commands.")

    while True:
        if _state["paused"]:
            time.sleep(10)
            continue

        if _state["force_topic"]:
            custom = _state["force_topic"]
            _state["force_topic"] = None
            do_post(forced_topic=None if custom=="__auto__" else custom)
            continue

        now_dt   = datetime.now()
        now_hm   = now_dt.strftime("%H:%M")
        today    = now_dt.strftime("%Y-%m-%d")
        time_key = f"{today}_{now_hm}"

        if now_hm in POST_TIMES and time_key not in _posted_today:
            _posted_today.add(time_key)
            do_post()
            
        time.sleep(30)

if __name__ == "__main__":
    # Start auto-poster background thread
    bot_thread = threading.Thread(target=bot_loop, daemon=True)
    bot_thread.start()
    
    # Start Flask server for Render health checks
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)