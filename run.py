import time
import random
import threading
import requests
import hashlib
from datetime import datetime
from pathlib import Path

import db
from config import (
    PAGE_ID, PAGE_ACCESS_TOKEN,
    APP_ID, APP_SECRET,
    TELEGRAM_BOT_TOKEN, TELEGRAM_USER_IDS,
    DEFAULT_LANGUAGE,
)
from topics import TOPICS
from ai_generator import generate_post, MODELS
import ai_generator
from image_maker import create_image

POST_TIMES = ["09:00", "14:00", "21:00"]
MAX_FB_RETRIES = 2
TOKEN_WARN_DAYS = 7
DAILY_TOKEN_WARN = 85_000

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

# Topic Queue
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

# Telegram
def mdv2(text: str) -> str:
    for ch in r"\_*[]()~`>#+-=|{}.!":
        text = text.replace(ch, f"\\{ch}")
    return text

def _send(uid: str, text: str, parse_mode: str = None):
    data = {"chat_id": uid.strip(), "text": text}
    if parse_mode:
        data["parse_mode"] = parse_mode
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            data=data, timeout=10,
        )
    except Exception:
        pass

def notify(text: str):
    for uid in TELEGRAM_USER_IDS.split(","):
        _send(uid, text)

def notify_md(text: str):
    for uid in TELEGRAM_USER_IDS.split(","):
        _send(uid, text, "MarkdownV2")

def notify_to(chat_id: str, text: str):
    _send(chat_id, text)

# Token expiry check
def check_token_expiry():
    if not APP_ID or not APP_SECRET:
        return
    try:
        res = requests.get(
            "https://graph.facebook.com/debug_token",
            params={"input_token": PAGE_ACCESS_TOKEN,
                    "access_token": f"{APP_ID}|{APP_SECRET}"},
            timeout=10,
        ).json()
        expires_at = res.get("data", {}).get("expires_at", 0)
        if expires_at == 0:
            notify("ℹ️ FB token permanent."); return
        exp_dt    = datetime.fromtimestamp(expires_at)
        days_left = (exp_dt - datetime.now()).days
        if days_left <= TOKEN_WARN_DAYS:
            notify(f"⚠️ FB Token {days_left} days left! Expiry: {exp_dt.strftime('%Y-%m-%d')}")
        else:
            notify(f"✅ FB Token OK — {days_left} days left")
    except Exception as e:
        print(f"Token check error: {e}")

# Facebook
def post_to_facebook(message: str, image_path: str) -> dict:
    url = f"https://graph.facebook.com/{PAGE_ID}/photos"
    with open(image_path, "rb") as img:
        res = requests.post(
            url,
            data={"caption": message, "access_token": PAGE_ACCESS_TOKEN, "published": "true"},
            files={"source": img},
            timeout=30,
        )
    result = res.json()
    if "error" in result:
        raise RuntimeError(result["error"].get("message", "FB error"))
    return result

# Core Post Action
def do_post(forced_topic: str = None):
    lang  = _lang()
    topic = forced_topic or next_topic()
    print(f"\n📝 [{lang.upper()}] Topic: {topic}")
    db.info("Post started", {"topic": topic, "language": lang})

    try:
        result = generate_post(topic, language=lang)
    except Exception as e:
        msg = f"❌ AI failed!\nTopic: {topic}\nError: {e}"
        print(msg); notify(msg)
        db.error("AI failed", {"topic": topic, "error": str(e)})
        return

    title   = result["title"]
    content = result["content"]

    if not content or len(content.strip()) < 80:
        msg = f"⚠️ Content too short — skip.\nTopic: {topic}"
        print(msg); notify(msg)
        return

    title_hash = hashlib.md5(title.encode('utf-8')).hexdigest()

    if db.is_title_used(title_hash):
        print("  ♻️ Duplicate title — regenerating...")
        db.warn("Duplicate title", {"title": title})
        try:
            result  = generate_post(topic, language=lang)
            title   = result["title"]
            content = result["content"]
            title_hash = hashlib.md5(title.encode('utf-8')).hexdigest()
        except Exception:
            pass

    print(f"  🏷  Title: {title}")

    try:
        # Pass positional arguments exactly to prevent language/topic mismatch
        image_path = create_image(title, topic, lang)
    except Exception as e:
        msg = f"❌ Image failed!\nError: {e}"
        print(msg); notify(msg)
        db.error("Image failed", {"error": str(e)})
        return

    fb_res = None
    for attempt in range(1, MAX_FB_RETRIES + 1):
        try:
            fb_res = post_to_facebook(f"{title}\n\n{content}", image_path)
            break
        except Exception as e:
            print(f"  ⚠️ FB attempt {attempt}: {e}")
            if attempt == MAX_FB_RETRIES:
                notify(f"❌ FB post failed!\nError: {e}")
                db.error("FB failed", {"error": str(e)})
                return
            time.sleep(10)

    post_id = fb_res.get("post_id", fb_res.get("id", "N/A"))
    print(f"  ✅ Posted: {post_id}")

    # Directly save to DB without relying on db.save_post function
    with db._conn() as c:
        c.execute(
            "INSERT INTO posts (topic, title, content, language, fb_post_id, created_at) VALUES (?,?,?,?,?,?)",
            (topic, title, content, lang, str(post_id), datetime.now().isoformat())
        )
    db.mark_title_used(title_hash, topic)
    db.info("Post success", {"topic": topic, "post_id": post_id})

    if db.get_daily_tokens() > DAILY_TOKEN_WARN:
        notify(f"⚠️ Token usage today: {db.get_daily_tokens():,}")

    # Quality score icons
    hs = result.get("human_score")
    fs = result.get("fact_score")
    src = result.get("sources_count", 0)
    dp  = result.get("deep_fetched", False)

    h_icon = "✅" if (hs or 0) >= 85 else "⚠️"
    f_icon = "✅" if fs is None or (fs or 0) >= 60 else "⚠️"

    h_line = f"{h_icon} Human Score : {hs}%" if hs is not None else ""
    if fs is not None:
        f_line = f"{f_icon} Fact Score  : {fs}%"
    else:
        f_line = "ℹ️  Fact Score  : Not checked (no search API)"
    src_line = f"🌐 Sources     : {src} {'+ deep fetch' if dp else ''}"

    now    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lang_l = "🇧🇩 বাংলা" if lang == "bn" else "🇬🇧 English"

    tg_msg = (
        "🚀 *New Post Created*\n\n"
        + f"📝 Topic: *{mdv2(topic)}*\n"
        + f"🏷 Title: *{mdv2(title)}*\n"
        + f"🌐 Language: {lang_l}\n\n"
        + f"🔬 *Quality Report*\n"
        + f"{mdv2(h_line)}\n"
        + f"{mdv2(f_line)}\n"
        + f"{mdv2(src_line)}\n\n"
        + f"🕒 {mdv2(now)}\n\n"
        + "📌 Post ID: ||" + mdv2(str(post_id)) + "||\n"
        + "👤 Page ID: ||" + mdv2(str(PAGE_ID)) + "||\n\n"
        + "📄 Preview:\n>" + mdv2(content[:180]) + "\\.\\.\\."
    )
    notify_md(tg_msg)

# Telegram Commands
ALLOWED_IDS = set(uid.strip() for uid in str(TELEGRAM_USER_IDS).split(","))

def handle_command(text: str, chat_id: str):
    parts = text.strip().split()
    cmd   = parts[0].lower()

    if cmd == "/post":
        custom = " ".join(parts[1:]) if len(parts) > 1 else None
        _state["force_topic"] = custom or "__auto__"
        msg = f'✅ Post queued: "{custom}"' if custom else "✅ Manual post queued!"
        notify_to(chat_id, msg)

    elif cmd == "/pause":
        _state["paused"] = True
        notify_to(chat_id, "⏸ Bot paused. Use /resume to start.")

    elif cmd == "/resume":
        _state["paused"] = False
        notify_to(chat_id, "▶️ Bot resumed.")

    elif cmd == "/lang":
        if len(parts) < 2 or parts[1].lower() not in ("bn","en"):
            notify_to(chat_id, "Usage: /lang bn  OR  /lang en"); return
        _state["language"] = parts[1].lower()
        notify_to(chat_id, f"🌐 Language → {'বাংলা 🇧🇩' if _state['language']=='bn' else 'English 🇬🇧'}")

    elif cmd == "/status":
        stats  = db.get_stats_summary()
        status = "⏸ Paused" if _state["paused"] else "▶️ Running"
        lang   = "বাংলা 🇧🇩" if _lang()=="bn" else "English 🇬🇧"
        model_label = ai_generator.PREFERRED_MODEL.split("/")[-1] if ai_generator.PREFERRED_MODEL else "Auto"
        
        tot_posts = stats.get('total_posts', 0)
        tdy_posts = stats.get('posts_today', stats.get('today_posts', 0))
        tdy_toks = stats.get('tokens_today', 0)
        last_p = stats.get('last_post', stats.get('last_post_time', 'Never'))
        
        notify_to(chat_id,
            f"📊 AutoPost Status\n\n"
            f"Status   : {status}\n"
            f"Language : {lang}\n"
            f"Model    : {model_label}\n"
            f"Schedule : {', '.join(POST_TIMES)}\n"
            f"Queue    : {len(_topic_queue)}/{len(TOPICS)} left\n\n"
            f"📈 Total posts  : {tot_posts}\n"
            f"📅 Posts today  : {tdy_posts}\n"
            f"🔤 Tokens today : {tdy_toks:,}\n"
            f"🕐 Last post    : {last_p}"
        )

    elif cmd == "/stats":
        stats = db.get_stats_summary()
        tot_posts = stats.get('total_posts', 0)
        tdy_posts = stats.get('posts_today', stats.get('today_posts', 0))
        tdy_toks = stats.get('tokens_today', 0)
        last_p = stats.get('last_post', stats.get('last_post_time', 'Never'))
        
        notify_to(chat_id,
            f"📈 Statistics\n\nTotal posts  : {tot_posts}\n"
            f"Posts today  : {tdy_posts}\n"
            f"Tokens today : {tdy_toks:,}\n"
            f"Last post    : {last_p}"
        )

    elif cmd == "/topics":
        lines = [f"📋 Topics ({len(TOPICS)} total)\n"]
        lines += [f"{i+1}. {t}" for i, t in enumerate(TOPICS)]
        msg = "\n".join(lines)
        notify_to(chat_id, msg[:4000] + ("\n..." if len(msg)>4000 else ""))

    elif cmd == "/schedule":
        notify_to(chat_id, "🕒 Schedule:\n" + "\n".join(f"• {t}" for t in POST_TIMES))

    elif cmd == "/model":
        send_model_keyboard(chat_id)

    elif cmd == "/logs":
        import sqlite3
        db_path = Path(__file__).parent / "autopost.db"
        try:
            with sqlite3.connect(db_path) as c:
                rows = c.execute(
                    "SELECT level, message, created_at FROM logs "
                    "WHERE level IN ('ERROR','WARN') ORDER BY id DESC LIMIT 5"
                ).fetchall()
            if rows:
                lines = "\n".join(f"[{r[0]}] {r[2][:16]} — {r[1]}" for r in rows)
                notify_to(chat_id, f"🔍 Recent Errors:\n\n{lines}")
            else:
                notify_to(chat_id, "✅ No recent errors.")
        except Exception as e:
            notify_to(chat_id, f"Log error: {e}")

    elif cmd == "/help":
        notify_to(chat_id,
            "📌 AutoPost Commands\n\n"
            "/post — Force post now\n"
            "/post <topic> — Post specific topic\n"
            "/pause — Pause bot\n"
            "/resume — Resume bot\n"
            "/lang bn|en — Change language\n"
            "/status — Full status\n"
            "/stats — Statistics\n"
            "/topics — Topic list\n"
            "/schedule — Post schedule\n"
            "/model — Model select\n"
            "/logs — Recent errors\n"
            "/help — Show help"
        )
    else:
        notify_to(chat_id, "❓ Unknown command. Type /help.")

# Model keyboard
def send_model_keyboard(chat_id: str):
    current = ai_generator.PREFERRED_MODEL or "auto"
    buttons = []
    for m in MODELS:
        short = m.split("/")[-1][:28]
        tick  = "✅ " if m == current else ""
        buttons.append([{"text": f"{tick}{short}", "callback_data": f"model:{m}"}])
    buttons.append([{"text": "🔄 Auto", "callback_data": "model:auto"}])
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": chat_id, "text": f"Current: *{current}*\nSelect model:",
                "parse_mode": "Markdown", "reply_markup": {"inline_keyboard": buttons},
            }, timeout=10,
        )
    except Exception as e:
        notify_to(chat_id, f"Error: {e}")

def answer_callback(callback_id: str):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery",
            data={"callback_query_id": callback_id}, timeout=5,
        )
    except Exception:
        pass

def bot_polling():
    print("🤖 Bot polling started")
    while True:
        try:
            res = requests.get(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates",
                params={"offset": _state["last_update"] + 1, "timeout": 20},
                timeout=25,
            ).json()
            for update in res.get("result", []):
                _state["last_update"] = update["update_id"]
                cb = update.get("callback_query")
                if cb:
                    cb_id, cb_data = cb["id"], cb.get("data","")
                    cb_uid = str(cb.get("from",{}).get("id",""))
                    answer_callback(cb_id)
                    if cb_uid in ALLOWED_IDS and cb_data.startswith("model:"):
                        sel = cb_data[6:]
                        if sel == "auto":
                            ai_generator.PREFERRED_MODEL = None
                            notify_to(cb_uid, "🔄 Model → Auto")
                        else:
                            ai_generator.PREFERRED_MODEL = sel
                            notify_to(cb_uid, f"✅ Model → {sel.split('/')[-1]}")
                    continue
                msg     = update.get("message", {})
                text    = msg.get("text", "")
                chat_id = str(msg.get("chat",{}).get("id",""))
                if text.startswith("/") and chat_id in ALLOWED_IDS:
                    print(f"📩 {text}")
                    handle_command(text, chat_id)
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(5)

from flask import Flask
import os

# Main
def run():
    print("🚀 AutoPost starting...")
    db.init_db()
    stats = db.get_stats_summary()
    tot_posts = stats.get('total_posts', 0)
    print(f"   DB ready — {tot_posts} posts | Lang: {_lang().upper()}")
    print(f"   Schedule — {', '.join(POST_TIMES)} | Topics: {len(TOPICS)}")
    check_token_expiry()
    threading.Thread(target=bot_polling, daemon=True).start()
    lang_l = "বাংলা 🇧🇩" if _lang()=="bn" else "English 🇬🇧"
    notify(
        f"🚀 AutoPost Running!\n🌐 {lang_l}\n📅 {', '.join(POST_TIMES)}\n"
        f"📈 Total: {tot_posts} posts\n/help for commands."
    )
    db.info("AutoPost started", {"language": _lang()})

    while True:
        if _state["paused"]:
            time.sleep(10); continue

        if _state["force_topic"]:
            custom = _state["force_topic"]
            _state["force_topic"] = None
            do_post(forced_topic=None if custom=="__auto__" else custom)
            continue

        now_dt   = datetime.now()
        now_hm   = now_dt.strftime("%H:%M")
        today    = now_dt.strftime("%Y-%m-%d")
        time_key = f"{today}_{now_hm}"

        for k in list(_posted_today):
            if not k.startswith(today):
                _posted_today.discard(k)

        if now_hm in POST_TIMES and time_key not in _posted_today:
            _posted_today.add(time_key)
            do_post()

        time.sleep(30)


# Flask Setup (For Render Health Checks)
app = Flask(__name__)

@app.route('/')
def keep_alive():
    return "AutoPost Bot is Running Perfectly!"

# Start the bot loop in a background thread so Gunicorn can run the Flask app
threading.Thread(target=run, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8080))
    app.run(host="0.0.0.0", port=port)