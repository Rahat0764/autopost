import re
import json
import hashlib
import requests
from datetime import datetime, timedelta
from pathlib import Path
from config import SERPER_API_KEY

SERPER_URL   = "https://google.serper.dev/search"
CACHE_DIR    = Path(__file__).parent.parent / "research_cache"
CACHE_TTL_H  = 24

DEEP_FETCH_DOMAINS = [
    "wikipedia.org", "goodreads.com", "britannica.com",
    "imdb.com", "sparknotes.com", "cliffsnotes.com",
    "ielts.org", "ets.org", "jasso.or.jp", "saudi",
    "scholarships.com", "studyabroad.com",
    "prothomalo.com", "thedailystar.net", "bdnews24.com",
]

CACHE_DIR.mkdir(parents=True, exist_ok=True)

def _build_queries(topic: str) -> list[str]:
    t = topic.lower()
    queries = [topic]

    if any(w in t for w in ["scholarship", "study in", "স্কলারশিপ", "visa", "saudi", "quota"]):
        queries = [
            f"{topic} official portal how to apply 2026 update",
            f"{topic} requirements exact quota seats details",
        ]
    elif any(w in t for w in ["book", "novel", "summary", "film", "movie", "গল্প"]):
        clean = re.sub(r"^(summary|review|book)\s+", "", t).strip()
        queries = [f"{clean} synopsis plot summary", f"{clean} goodreads review"]
    elif any(w in t for w in ["ielts", "toefl", "exam", "test"]):
        queries = [f"{topic} 2026 test dates schedule", f"{topic} preparation tips scoring"]
    elif any(w in t for w in ["docker", "api", "cloud", "tech", "python"]):
        queries = [f"{topic} best practices 2026", f"{topic} overview examples"]
    else:
        queries = [f"{topic} specific facts details 2026", f"{topic} explained"]

    return queries[:2]

def _cache_key(topic: str) -> str:
    return hashlib.md5(topic.lower().strip().encode()).hexdigest()[:12]

def _load_cache(topic: str) -> dict | None:
    path = CACHE_DIR / f"{_cache_key(topic)}.json"
    if not path.exists(): return None
    try:
        data = json.loads(path.read_text("utf-8"))
        ts   = datetime.fromisoformat(data["timestamp"])
        if datetime.now() - ts < timedelta(hours=CACHE_TTL_H):
            return data
    except Exception: pass
    return None

def _save_cache(topic: str, data: dict):
    try:
        path = CACHE_DIR / f"{_cache_key(topic)}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
    except Exception: pass

def _serper_search(query: str, num: int = 6) -> list[dict]:
    if not SERPER_API_KEY: return []
    try:
        res  = requests.post(
            SERPER_URL,
            headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
            json={"q": query, "gl": "bd", "hl": "en", "num": num},
            timeout=10,
        )
        data = res.json()
    except Exception: return []

    results = []
    ab = data.get("answerBox", {})
    if ab.get("answer") or ab.get("snippet"):
        results.append({
            "title": ab.get("title", "Answer"),
            "snippet": ab.get("answer") or ab.get("snippet", ""),
            "link": ab.get("link", ""), "source": "answer_box"
        })

    for item in data.get("organic", [])[:num]:
        if item.get("title") and item.get("snippet"):
            results.append({
                "title": item["title"], "snippet": item["snippet"],
                "link": item.get("link", ""), "source": item.get("displayLink", "")
            })
    return results

def _fetch_page(url: str, max_chars: int = 5000) -> str:
    # set max_chars to 5000 so it captures specifics deeply hidden in text
    if not url or not any(d in url for d in DEEP_FETCH_DOMAINS): return ""
    try:
        r = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"}, allow_redirects=True)
        text = re.sub(r"<script[^>]*>.*?</script>", " ", r.text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) > 300:
            return text[:max_chars]
    except Exception: pass
    return ""

def _format_context(results: list[dict], deep_content: str, topic: str) -> str:
    if not results and not deep_content: return ""
    parts = [f"=== WEB RESEARCH ==="]
    if deep_content: parts.append(f"\n[FULL PAGE CONTENT]\n{deep_content}")
    for i, r in enumerate(results[:8], 1):
        if r.get('title') and r.get('snippet'):
            parts.append(f"\n[{i}] {r['title']}\n    {r['snippet']}")
    return "\n".join(parts)

def research(topic: str) -> dict:
    empty = {"context_text": "", "sources_count": 0, "found": False, "deep_fetched": False}
    if not SERPER_API_KEY: return empty

    cached = _load_cache(topic)
    if cached: return cached

    queries = _build_queries(topic)
    all_results, seen_links = [], set()

    for q in queries:
        for r in _serper_search(q, num=6):
            key = r.get("link", "") or r.get("title", "")
            if key and key not in seen_links:
                seen_links.add(key)
                all_results.append(r)

    deep_content = ""
    for r in all_results:
        dc = _fetch_page(r.get("link", ""))
        if dc:
            deep_content = dc
            break

    result = {
        "context_text": _format_context(all_results, deep_content, topic),
        "sources_count": len(all_results),
        "queries": queries,
        "found": bool(all_results),
        "deep_fetched": bool(deep_content),
        "topic": topic,
        "timestamp": datetime.now().isoformat(),
    }
    _save_cache(topic, result)
    return result