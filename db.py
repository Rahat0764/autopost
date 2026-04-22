import sqlite3
import json
import hashlib
from datetime import datetime, date
from pathlib import Path

DB_PATH = Path(__file__).parent / "autopost.db"

def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Creates database and all tables if they do not exist."""
    with _conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS posts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            topic       TEXT    NOT NULL,
            title       TEXT    NOT NULL,
            content     TEXT    NOT NULL,
            language    TEXT    NOT NULL DEFAULT 'bn',
            fb_post_id  TEXT,
            created_at  TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS used_titles (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title_hash  TEXT    UNIQUE NOT NULL,
            topic       TEXT,
            created_at  TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            level       TEXT    NOT NULL,
            message     TEXT    NOT NULL,
            extra       TEXT,
            created_at  TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS token_usage (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            date        TEXT    NOT NULL,
            api_key_idx INTEGER NOT NULL DEFAULT 0,
            model       TEXT    NOT NULL,
            tokens      INTEGER NOT NULL,
            UNIQUE(date, api_key_idx, model)
        );
        """)

def info(msg: str, extra: dict = None):
    _log("INFO", msg, extra)

def warn(msg: str, extra: dict = None):
    _log("WARN", msg, extra)

def error(msg: str, extra: dict = None):
    _log("ERROR", msg, extra)

def _log(level: str, msg: str, extra: dict = None):
    ex_str = json.dumps(extra, ensure_ascii=False) if extra else None
    now = datetime.now().isoformat()
    with _conn() as c:
        c.execute(
            "INSERT INTO logs (level, message, extra, created_at) VALUES (?,?,?,?)",
            (level, msg, ex_str, now)
        )

def get_recent_topics(limit: int = 10) -> list[str]:
    with _conn() as c:
        rows = c.execute("SELECT topic FROM posts ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [r["topic"] for r in rows]

# --- Helper functions added for run.py and ai_generator.py compatibility ---

def track_tokens(api_key_idx: int, model: str, tokens: int):
    """Tracks token usage by calling the existing add_token_usage function."""
    add_token_usage(api_key_idx, model, tokens)

def is_title_duplicate(title: str) -> bool:
    """Checks if a title already exists by hashing it."""
    title_hash = hashlib.md5(title.encode('utf-8')).hexdigest()
    return is_title_used(title_hash)

def save_post(topic: str, title: str, content: str, language: str, fb_post_id: str):
    """Saves a successfully generated post and its title hash to the database."""
    now = datetime.now().isoformat()
    title_hash = hashlib.md5(title.encode('utf-8')).hexdigest()
    with _conn() as c:
        c.execute(
            "INSERT INTO posts (topic, title, content, language, fb_post_id, created_at) VALUES (?,?,?,?,?,?)",
            (topic, title, content, language, fb_post_id, now)
        )
    mark_title_used(title_hash, topic)

# -------------------------------------------------------------------------

def is_title_used(title_hash: str) -> bool:
    with _conn() as c:
        row = c.execute("SELECT id FROM used_titles WHERE title_hash=?", (title_hash,)).fetchone()
        return bool(row)

def mark_title_used(title_hash: str, topic: str):
    now = datetime.now().isoformat()
    with _conn() as c:
        c.execute(
            "INSERT OR IGNORE INTO used_titles (title_hash, topic, created_at) VALUES (?,?,?)",
            (title_hash, topic, now)
        )

def add_token_usage(api_key_idx: int, model: str, tokens: int):
    today = date.today().isoformat()
    with _conn() as c:
        c.execute("""
            INSERT INTO token_usage (date, api_key_idx, model, tokens)
            VALUES (?,?,?,?)
            ON CONFLICT(date, api_key_idx, model) DO UPDATE SET tokens = tokens + excluded.tokens
        """, (today, api_key_idx, model, tokens))

def get_daily_tokens(api_key_idx: int = None) -> int:
    today = date.today().isoformat()
    with _conn() as c:
        if api_key_idx is not None:
            row = c.execute(
                "SELECT SUM(tokens) FROM token_usage WHERE date=? AND api_key_idx=?",
                (today, api_key_idx)
            ).fetchone()
        else:
            row = c.execute(
                "SELECT SUM(tokens) FROM token_usage WHERE date=?", (today,)
            ).fetchone()
        return row[0] or 0

def get_stats_summary() -> dict:
    with _conn() as c:
        total  = c.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
        today  = date.today().isoformat()
        today_count = c.execute(
            "SELECT COUNT(*) FROM posts WHERE created_at LIKE ?", (f"{today}%",)
        ).fetchone()[0]
        tokens_today = c.execute(
            "SELECT SUM(tokens) FROM token_usage WHERE date=?", (today,)
        ).fetchone()[0] or 0
        last = c.execute(
            "SELECT created_at FROM posts ORDER BY id DESC LIMIT 1"
        ).fetchone()
        
        return {
            "total_posts": total,
            "posts_today": today_count,
            "tokens_today": tokens_today,
            "last_post": last[0] if last else None
        }
