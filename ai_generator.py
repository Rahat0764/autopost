import re
import time
import random
import requests
from datetime import datetime
import db
from config import GEMINI_API_KEYS
from web_search import research as do_research
from checker import check_post, strip_excess_emojis, HUMAN_PASS, MAX_EMOJI

DAILY_LIMIT = 90_000

_key_cooldowns: dict[int, float] = {}

# Session 
def _year()  -> int:  return datetime.now().year
def _year2() -> int:  return datetime.now().year + 1
def _ay()    -> str:  return f"{_year()}–{_year2()}"

# Gemini Models
MODELS = [
    "gemini-2.5-flash", # 5 RPM, 250K TPM
    "gemini-2.5-flash-lite", # 10 RPM, 250K TPM
    "gemini-3-flash-preview", # 5 RPM, 250K TPM
    "gemini-3.1-flash-lite-preview", # 15 RPM, 250K TPM
]

PREFERRED_MODEL: str | None = None
_breaker: dict[str, int] = {}
BREAKER_THRESHOLD = 3
MAX_RETRIES = 2

# Angles
ANGLES_BN = [
    "Give direct guidelines and main facts without any fluff.",
    "Point out the biggest mistake people make, and provide a solution.",
    "Give specific and lesser-known details about this topic.",
]
ANGLES_EN = [
    "Give direct facts and guidelines without any fluff.",
    "Point out the biggest misconception and provide data to solve it.",
    "Provide specific, lesser-known details about this topic.",
]

# Profile detector
def _detect_profile(topic: str, cy: int, ay: str) -> dict:
    t = topic.lower()
    if any(w in t for w in [
        "scholarship", "study in", "visa", "abroad", "saudi", "quota",
    ]):
        return {
            "bn": {
                "role": f"You are an expert consultant. Academic year: {ay}.",
                "guide": (
                    "Extract specific facts from research data. "
                    "Do not miss portal names, quotas, or deadlines. "
                    "Do not repeat any sentences."
                ),
            },
            "en": {
                "role": f"You are an expert immigration consultant. Academic year: {ay}.",
                "guide": (
                    "Extract specific data from research. "
                    "Portal names, exact quotas, deadlines must be included. "
                    "Never repeat sentences."
                ),
            },
        }
    return {
        "bn": {
            "role": f"You are a smart content creator. Current year: {cy}.",
            "guide": (
                "Organize exact facts from research data. "
                "Do not repeat the same points. "
                "Write in a casual yet professional tone like a human."
            ),
        },
        "en": {
            "role": f"You are a smart content creator. Current year: {cy}.",
            "guide": (
                "Organize exact facts from research data. "
                "NEVER repeat the same points. "
                "Write in a casual yet professional, highly human tone."
            ),
        },
    }

# Parse / Validate helpers
def _norm(s: str) -> str:
    return re.sub(r"[^\w\s]", "", s.lower()).strip()

def _is_same(title: str, topic: str) -> bool:
    nt, tp = _norm(title), _norm(topic)
    if nt == tp:
        return True
    if len(tp) >= 8:
        tw = set(tp.split())
        nw = set(nt.split())
        if len(tw) > 0 and len(nw & tw) / len(tw) >= 0.90:
            return True
    return False

def _parse(raw: str, fallback: str) -> dict:
    lines = raw.strip().splitlines()
    title, body = "", []

    for line in lines:
        s       = line.strip()
        s_clean = s.strip("*_# ")
        if not title and re.match(r"^title\s*:", s_clean, re.IGNORECASE):
            cand = re.sub(r"^title\s*:\s*", "", s_clean, flags=re.IGNORECASE).strip("*_\"' ")
            if len(cand) >= 5:
                title = cand
            continue
        body.append(line)

    if not title or _is_same(title, fallback):
        title, new_body = "", []
        for line in body:
            s = line.strip()
            if not title and s:
                m = re.match(r"^\*\*(.+?)\*\*$", s) or re.match(r"^__(.+?)__$", s)
                h = re.match(r"^#{1,3}\s+(.+)$", s)
                cand = (m.group(1) if m else None) or (h.group(1) if h else None)
                if cand and len(cand) >= 5 and not _is_same(cand, fallback):
                    title = cand.strip("*_\"' ")
                    continue
            new_body.append(line)
        body = new_body

    if not title:
        title = fallback

    content = "\n".join(body).strip()
    content = re.sub(r'\*\*(.*?)\*\*', r'\1', content)
    content = re.sub(r'__(.*?)__',     r'\1', content)
    content = re.sub(r'\*(.*?)\*',     r'\1', content)
    content = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\1 (\2)', content)

    content = strip_excess_emojis(content, MAX_EMOJI)
    return {"title": title, "content": content}

def _validate(result: dict, language: str, topic: str) -> tuple[bool, str]:
    t, c = result.get("title", ""), result.get("content", "")
    if not t or len(t.strip()) < 5:
        return False, "Title missing"
    if _is_same(t, topic):
        return False, f"Title = Topic: '{t[:60]}'"
    if not c or len(c.strip()) < 120:
        return False, f"Content too short ({len(c)})"
    if "#" not in c:
        return False, "Hashtags missing"
    lines = [l.strip() for l in c.splitlines() if len(l.strip()) > 20]
    for line in set(lines):
        if lines.count(line) >= 3:
            return False, "Repetition bug"
    return True, "OK"

# Prompt Builder
def _build_prompt(
    topic: str,
    language: str,
    profile: dict,
    angle: str,
    research_ctx: str,
    bad_title: str = "",
) -> str:
    cy, ay = _year(), _ay()
    p      = profile.get(language) or profile.get("bn")
    lang   = language.lower()

    if lang == "bn":
        bad_ex   = topic[:60]
        good_ex  = _generate_title_example(topic, "bn")
        title_block = f"""
════ TITLE GENERATION (Do this first) ════
Create an engaging title.

❌ DO NOT use this as the title (this is the topic):
   "{bad_ex}"

✅ Create something like this (example only):
   "{good_ex}"

Rules:
- Do not copy the topic words verbatim.
- Create curiosity.
- Keep it between 8 to 15 words.
{("⚠️ Your previous title (" + bad_title[:50] + ") was rejected for being too similar to the topic. Give a completely new one.") if bad_title else ""}
════════════════════════════════════════════
"""
        lang_inst    = "Write the entire post in Bengali language."
        hashtag_note = "MANDATORY: Give 5-7 relevant hashtags at the very end."
        emoji_rule   = f"Maximum {MAX_EMOJI} emojis — only at paragraph breaks."
        style_note   = (
            "Facebook plain text — no Markdown (Bold, Links). Provide direct URLs like 'Visit: www.site.com'. "
            "Ban AI phrases. Never repeat the same sentences. Act like a human."
        )
    else:
        bad_ex  = topic[:60]
        good_ex = _generate_title_example(topic, "en")
        title_block = f"""
════ TITLE GENERATION (do this first) ════
Create a catchy title for this post.

❌ DO NOT use this as title (this is the topic):
   "{bad_ex}"

✅ Create something like this (example only):
   "{good_ex}"

Rules:
- Do NOT copy the topic words verbatim
- Must create curiosity in the reader
- Keep it 8–15 words
{("⚠️ Your previous title (" + bad_title[:50] + ") was rejected — it was too similar to the topic. Give a completely different one.") if bad_title else ""}
════════════════════════════════════════════
"""
        lang_inst    = "Write the entire post in English."
        hashtag_note = "MANDATORY: End with 5-7 relevant hashtags."
        emoji_rule   = f"Maximum {MAX_EMOJI} emojis — only at paragraph breaks."
        style_note   = (
            "Facebook plain text — no **Bold** or [Link](url) Markdown. If needs, give direct url example 'Visit: www.*****.com' "
            "Ban: moreover, in conclusion, it is important to note. Avoid AI type generation, generate post as if you are a human. "
            "Never repeat the same sentences."
        )

    research_block = ""
    if research_ctx:
        research_block = f"""
--- LIVE RESEARCH DATA (use specific facts, numbers, links from here) ---
{research_ctx}
-------------------------------------------------------------------------
"""

    return f"""\
{p["role"]}
{title_block}
Topic: {topic}
Angle: {angle}

{lang_inst}
{research_block}

--- OUTPUT FORMAT ---
TITLE: <your unique title>

<post body — PLAIN TEXT only, no Markdown>

--- Writing Guide ---
{p["guide"]}
{emoji_rule}
{style_note}
{hashtag_note}
"""

def _generate_title_example(topic: str, lang: str) -> str:
    t = topic.lower()
    if lang == "bn":
        if any(w in t for w in ["tourism", "travel"]):
            return "বাংলাদেশ ভ্রমণে যে ৫টি সমস্যা কেউ বলে না"
        if any(w in t for w in ["ielts", "sat", "exam"]):
            return "পরীক্ষার আগের রাতে যে ভুলটি সবাই করে"
        if any(w in t for w in ["scholarship", "study", "visa"]):
            return "এই স্কলারশিপে সুযোগ ছিল অথচ আপনি আবেদন করেননি"
        if any(w in t for w in ["tech", "software", "python"]):
            return "সিনিয়র ডেভেলপাররা যে কাজটি কখনো করে না"
        return "যে বিষয়টি সবাই জানে, কিন্তু কেউ মানে না"
    else:
        if any(w in t for w in ["tourism", "travel"]):
            return "5 Tourism Problems Nobody Talks About"
        if any(w in t for w in ["ielts", "sat", "exam"]):
            return "The Night-Before Mistake Every Student Makes"
        if any(w in t for w in ["scholarship", "study", "visa"]):
            return "The Scholarship Opportunity You Probably Missed"
        if any(w in t for w in ["tech", "software", "python"]):
            return "What Senior Devs Never Do (And Why)"
        return "What Everyone Knows But Nobody Actually Does"

# Gemini API Call
def call_gemini(prompt: str, model: str, api_key: str):
    url     = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.75, "maxOutputTokens": 2048},
    }
    try:
        res  = requests.post(
            url, json=payload,
            headers={"Content-Type": "application/json"},
            timeout=45,
        )
        data = res.json()
        if res.status_code != 200:
            return None, data.get("error", {}).get("message", str(res.status_code)), 0
        text   = data["candidates"][0]["content"]["parts"][0]["text"]
        tokens = data.get("usageMetadata", {}).get("totalTokenCount", 0)
        return text.strip(), "", tokens
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
        return None, f"Connection error: {e}", 0
    except (KeyError, IndexError):
        return None, "Invalid response structure", 0
    except Exception as e:
        return None, str(e), 0

# Core Generator
def generate_post(topic: str, language: str = "bn") -> dict:
    if not GEMINI_API_KEYS:
        raise RuntimeError("GEMINI_API_KEY is not set in .env!")

    lang    = language.lower()
    cy, ay  = _year(), _ay()
    rdata   = do_research(topic)
    print(f"  📚 Research: {rdata['sources_count']} sources, "
          f"deep={rdata['deep_fetched']}, found={rdata['found']}")

    profile = _detect_profile(topic, cy, ay)
    angle   = random.choice(ANGLES_BN if lang == "bn" else ANGLES_EN)
    last_err = "Unknown"
    bad_title_from_retry = ""

    model_list = MODELS.copy()
    if PREFERRED_MODEL and PREFERRED_MODEL in model_list:
        model_list.remove(PREFERRED_MODEL)
        model_list.insert(0, PREFERRED_MODEL)

    for key_idx, api_key in enumerate(GEMINI_API_KEYS):
        if _key_cooldowns.get(key_idx, 0) > time.time():
            continue
        if db.get_daily_tokens(key_idx) >= DAILY_LIMIT:
            continue

        for model in model_list:
            if _breaker.get(model, 0) >= BREAKER_THRESHOLD:
                continue

            key_exhausted = False

            for attempt in range(1, MAX_RETRIES + 1):
                prompt = _build_prompt(
                    topic, lang, profile, angle,
                    rdata.get("context_text", ""),
                    bad_title_from_retry,
                )
                print(f"  🤖 Key{key_idx+1} [{lang.upper()}] {model} attempt {attempt}...")

                raw_text, err_msg, tokens = call_gemini(prompt, model, api_key)

                if err_msg:
                    last_err = err_msg
                    is_quota = (
                        "429" in str(err_msg)
                        or "quota" in str(err_msg).lower()
                        or "exhausted" in str(err_msg).lower()
                    )
                    if is_quota:
                        m = re.search(r"retry in (\d+\.?\d*)s", str(err_msg))
                        wait_t = float(m.group(1)) + 1.5 if m else 65.0
                        if wait_t > 30:
                            print(f"  ⏳ Quota wait too long ({wait_t:.1f}s) — Switching Key!")
                            _key_cooldowns[key_idx] = time.time() + wait_t
                            key_exhausted = True
                            break
                        else:
                            print(f"  ⏳ Quota limit hit! Waiting {wait_t:.1f}s...")
                            time.sleep(wait_t)
                            continue
                    else:
                        _breaker[model] = _breaker.get(model, 0) + 1
                        break

                if key_exhausted:
                    break

                if not raw_text:
                    last_err = "Empty response"
                    continue

                if tokens:
                    db.add_token_usage(key_idx, model, tokens)

                parsed = _parse(raw_text, topic)
                ok, reason = _validate(parsed, lang, topic)
                if not ok:
                    last_err = reason
                    print(f"  ⚠️ Validation fail: {reason}")
                    if "Title = Topic" in reason:
                        bad_title_from_retry = parsed.get("title", "")
                    continue

                check = check_post(parsed["content"], rdata, lang)
                if not check["passed"] and attempt < MAX_RETRIES:
                    print(f"  🔄 Quality low (H:{check['human_score']}%) — retry")
                    continue

                _breaker[model] = 0
                icon = "✅" if check["passed"] else "⚠️"
                print(f"  {icon} {model} | H:{check['human_score']}% "
                      f"F:{check['fact_score']}% | {parsed['title'][:50]}")

                db.info("Post generated", {
                    "topic": topic, "model": model, "tokens": tokens,
                    "title": parsed["title"],
                    "human_score": check["human_score"],
                    "fact_score":  check["fact_score"],
                })

                return {
                    **parsed,
                    "model":          model,
                    "tokens":         tokens,
                    "human_score":    check["human_score"],
                    "fact_score":     check["fact_score"],
                    "quality_report": check["report"],
                    "sources_count":  rdata["sources_count"],
                    "deep_fetched":   rdata["deep_fetched"],
                    "searched":       rdata["found"],
                }

            if key_exhausted:
                break

    db.error("All keys/models failed", {"topic": topic, "last_error": last_err})
    raise RuntimeError(f"All API keys failed. Last error: {last_err}")