import re
from collections import Counter

# Emoji Detection
EMOJI_RE = re.compile(
    "[\U0001F600-\U0001F64F"   # Emoticons
    "\U0001F300-\U0001F5FF"    # Symbols & pictographs
    "\U0001F680-\U0001F6FF"    # Transport & map
    "\U0001F900-\U0001F9FF"    # Supplemental symbols
    "\U00002600-\U000026FF"    # Misc symbols
    "\U00002700-\U000027BF"    # Dingbats
    "\U0001F1E0-\U0001F1FF"    # Flags
    "\U00010000-\U0010FFFF"    # Other emoji ranges
    "]",
    flags=re.UNICODE,
)

MAX_EMOJI = 2   # iron-clad limit

# AI Phrase Lists
EN_AI_PHRASES = [
    "moreover", "furthermore", "in conclusion", "it is worth noting",
    "it is important to note", "delve into", "in the realm of",
    "first and foremost", "last but not least", "needless to say",
    "it goes without saying", "in today's world", "in today's fast",
    "without further ado", "let's dive in", "let's explore",
    "as we know", "as mentioned", "in summary", "to summarize",
    "to conclude", "in a nutshell", "the bottom line",
    "as a result of", "due to the fact that", "it should be noted",
    "it is clear that", "it is evident", "it can be seen",
]

BN_AI_PHRASES = [
    "উল্লেখযোগ্য যে", "বিশেষভাবে উল্লেখ্য", "সর্বোপরি",
    "পরিশেষে বলা যায়", "নিঃসন্দেহে", "বলা বাহুল্য",
    "অনস্বীকার্য", "প্রথমত", "দ্বিতীয়ত", "তৃতীয়ত",
    "এটি উল্লেখ করা প্রয়োজন", "সুস্পষ্টভাবে", "সামগ্রিকভাবে",
    "সার্বিকভাবে", "একটি সমৃদ্ধ", "এই প্রেক্ষাপটে",
    "বিস্তারিত আলোচনা", "গভীরভাবে বিশ্লেষণ",
]

# Emoji Stripper (post-processing)
def strip_excess_emojis(text: str, max_count: int = MAX_EMOJI) -> str:
    """MAX_EMOJI এর বেশি emoji মুছে দেয়।"""
    count   = 0
    result  = []
    i       = 0
    chars   = list(text)
    while i < len(chars):
        ch = chars[i]
        if EMOJI_RE.match(ch):
            count += 1
            if count <= max_count:
                result.append(ch)
            # else: skip
        else:
            result.append(ch)
        i += 1
    return "".join(result)

# Human Score (Heuristic)
def score_human(content: str, language: str = "bn") -> tuple[int, list[str]]:
    """
    0–100 human-likeness score.
    Returns (score, issues_list).
    """
    score  = 100
    issues = []
    text_l = content.lower()

    # 1. Emoji count
    emojis = EMOJI_RE.findall(content)
    emoji_count = len(emojis)
    if emoji_count > MAX_EMOJI:
        penalty = min((emoji_count - MAX_EMOJI) * 6, 30)
        score  -= penalty
        issues.append(f"Emoji অতিরিক্ত: {emoji_count}টা (max {MAX_EMOJI})")

    # 2. AI phrases
    all_phrases = EN_AI_PHRASES + BN_AI_PHRASES
    found = [p for p in all_phrases if p in text_l]
    if found:
        penalty = min(len(found) * 4, 28)
        score  -= penalty
        issues.append(f"AI phrase: {', '.join(found[:3])}")

    # 3. Numbered list overuse (১. ২. ৩. or 1. 2. 3.)
    num_lines = re.findall(
        r"^[\d১২৩৪৫৬৭৮৯0-9][।\.\)]\s",
        content, re.MULTILINE
    )
    if len(num_lines) > 5:
        score  -= 10
        issues.append(f"অতিরিক্ত numbered list: {len(num_lines)} items")

    # 4. Repetitive paragraph starters
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
    if paragraphs:
        starters = []
        for p in paragraphs:
            words = p.split()
            if words:
                starters.append(words[0].lower().strip("*_#"))
        cnt = Counter(starters)
        for starter, c in cnt.items():
            if c >= 3 and len(starter) > 2:
                score  -= 8
                issues.append(f"Paragraph একই শব্দ দিয়ে শুরু: '{starter}' × {c}")
                break

    # 5. Very short content (< 200 chars)
    if len(content) < 200:
        score  -= 15
        issues.append("Content অনেক ছোট")

    # 6. Too few paragraphs
    if len(paragraphs) < 3:
        score  -= 8
        issues.append(f"Paragraph কম: {len(paragraphs)} (min 3)")

    # 7. Missing hashtags (Bengali)
    if language == "bn" and "#" not in content:
        score  -= 5
        issues.append("Hashtag নেই")

    # 8. Reasoning tag leak
    if re.search(r"<think|<thinking|<reasoning", content, re.IGNORECASE):
        score  -= 40
        issues.append("AI reasoning tag leaked!")

    return max(0, min(100, score)), issues

# Fact Score (Search Overlap Proxy)
def score_facts(content: str, research: dict) -> tuple[int | None, str]:
    """
    Search context vs post content overlap proxy.
    Returns (score or None, explanation).
    """
    context = research.get("context_text", "")
    found   = research.get("found", False)

    if not context or not found:
        return None, "Search data নেই (SERPER_API_KEY নেই বা result শূন্য)"

    sources = research.get("sources_count", 0)
    deep    = research.get("deep_fetched", False)

    # Extract meaningful words (4+ chars) from both
    def words(text: str) -> set:
        return {
            w.lower() for w in re.findall(r"[A-Za-z\u0980-\u09FF]{4,}", text)
            if len(w) >= 4
        }

    ctx_words  = words(context)
    post_words = words(content)

    if not ctx_words:
        return 70, "Research context পাতলা"

    overlap  = len(ctx_words & post_words)
    base     = min(100, int(overlap / max(len(ctx_words) * 0.25, 15) * 100))

    # Bonuses
    if deep:
        base = max(base, 72)   # deep fetch was done
    if sources >= 5:
        base = max(base, 68)
    elif sources >= 3:
        base = max(base, 62)
    elif sources >= 1:
        base = max(base, 55)

    score = min(100, base)
    note  = f"{sources} sources, {'deep fetch' if deep else 'snippets only'}, {overlap} word overlap"
    return score, note

# Combined Check
HUMAN_PASS  = 85   # minimum human score to post
FACT_PASS   = 60   # minimum fact score to post (when search data exists)

def check_post(content: str, research: dict, language: str = "bn") -> dict:
    """
    Full quality check।
    Returns:
      human_score: int
      fact_score: int | None
      human_issues: list
      fact_note: str
      passed: bool
      report: str  (Telegram-ready)
    """
    human_score, human_issues = score_human(content, language)
    fact_score,  fact_note    = score_facts(content, research)

    human_ok = human_score >= HUMAN_PASS
    fact_ok  = (fact_score is None) or (fact_score >= FACT_PASS)
    passed   = human_ok and fact_ok

    # ── Telegram report ──
    h_icon = "✅" if human_ok else "⚠️"
    f_icon = "✅" if fact_ok  else "⚠️"

    lines = [
        f"{'✅ PASSED' if passed else '⚠️ QUALITY ISSUE'}",
        f"",
        f"{h_icon} Human Score : {human_score}%",
    ]
    if human_issues:
        lines.append(f"   Issues: {' | '.join(human_issues[:2])}")

    if fact_score is not None:
        lines.append(f"{f_icon} Fact Score  : {fact_score}%")
        lines.append(f"   {fact_note}")
    else:
        lines.append(f"ℹ️  Fact Score  : Not checked")
        lines.append(f"   {fact_note}")

    report = "\n".join(lines)
    return {
        "human_score":  human_score,
        "fact_score":   fact_score,
        "human_issues": human_issues,
        "fact_note":    fact_note,
        "passed":       passed,
        "report":       report,
    }