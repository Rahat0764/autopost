from PIL import Image, ImageDraw, ImageFont
import os

BASE_DIR  = os.path.dirname(os.path.dirname(__file__))
FONTS_DIR = os.path.join(BASE_DIR, "fonts")

# Themes
THEMES = {
    "tech":        {"bg": "#0a0f2c", "accent": "#00c6ff"},
    "language":    {"bg": "#071a10", "accent": "#00e676"},
    "consultancy": {"bg": "#0d1117", "accent": "#f0b429"},
    "education":   {"bg": "#0f1a2e", "accent": "#e8a020"},   # deep navy + warm gold
    "history":     {"bg": "#1a1208", "accent": "#d4a853"},
    "horror":      {"bg": "#0f0508", "accent": "#cc2222"},
    "default":     {"bg": "#0a0f2c", "accent": "#00c6ff"},
}

THEME_KEYWORDS = {
    "tech": [
        "tech", "software", "developer", "programming", "code", "docker", "api",
        "backend", "frontend", "cloud", "devops", "system design", "সফটওয়্যার",
        "প্রোগ্রামিং", "ডেভেলপার", "ডকার", "ডেটাবেস", "স্কেলেবল", "আর্কিটেকচার",
        "মাইক্রোসার্ভিস", "python", "javascript", "java", "sql", "nosql",
        "git", "ci/cd", "rest", "graphql", "async", "microservice",
    ],
    "language": [
        "ielts", "toefl", "jlpt", "gre", "gmat", "sat", "japanese", "korean",
        "french", "german", "spanish", "chinese", "ভাষা", "language", "grammar",
        "পরীক্ষা", "band score", "toeic", "n1", "n2", "n3", "n4", "n5",
        "speaking", "writing", "listening", "reading",
    ],
    "consultancy": [
        "জাপান", "কানাডা", "অস্ট্রেলিয়া", "জার্মানি", "uk", "usa", "ইউরোপ",
        "visa", "ভিসা", "scholarship", "স্কলারশিপ", "বিদেশ", "migration", "abroad",
        "mext", "chevening", "erasmus", "gks", "subclass", "f-1", "work permit",
        "singapore", "সিঙ্গাপুর", "dubai", "দুবাই", "korea", "কোরিয়া", "malaysia",
    ],
    "education": [
        "admission", "ভর্তি", "hsc", "ssc", "buet", "medical", "mbbs",
        "ঢাকা বিশ্ববিদ্যালয়", "বিশ্ববিদ্যালয়", "university", "coaching",
        "পড়াশোনা", "study tips", "study technique", "exam preparation",
        "একাডেমিক", "note", "memory", "concentration", "মনোযোগ", "মুখস্ত",
        "pomodoro", "spaced repetition", "active recall", "রাত জেগে",
        "exam anxiety", "শিক্ষা", "syllabus", "routine", "study routine",
        "পরিকল্পনা", "ভর্তি পরীক্ষা", "du", "dhaka university",
    ],
    "history": [
        "ইতিহাস", "history", "মুক্তিযুদ্ধ", "যুদ্ধ", "war", "সভ্যতা",
        "civilization", "empire", "সাম্রাজ্য", "revolution", "মুঘল", "mughal",
        "ottoman", "british", "রাজবংশ", "dynasty", "world war",
    ],
    "horror": [
        "horror", "হরর", "ভূত", "ghost", "ভৌতিক", "supernatural", "haunted",
        "ভয়", "demon", "spirit", "mystery", "অভিশপ্ত", "paranormal",
    ],
}


def detect_theme(text: str) -> dict:
    t = text.lower()
    # Priority order: specific themes before default
    for key in ["education", "consultancy", "language", "tech", "history", "horror"]:
        if any(kw in t for kw in THEME_KEYWORDS[key]):
            return THEMES[key]
    return THEMES["default"]

# Font loader
def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    path = os.path.join(FONTS_DIR, name)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Font not found: {path}")
    return ImageFont.truetype(path, size)


def _best_font(bold: bool, size: int, language: str) -> ImageFont.FreeTypeFont:
    """Language অনুযায়ী সেরা available font লোড করে।"""
    if language == "en":
        candidates = [
            ("NotoSerif-Bold.ttf"    if bold else "NotoSerif-Regular.ttf"),
            ("NotoSerifBengali-Bold.ttf" if bold else "NotoSerifBengali-Regular.ttf"),
        ]
    else:
        candidates = [
            ("NotoSerifBengali-Bold.ttf" if bold else "NotoSerifBengali-Regular.ttf"),
        ]
    for name in candidates:
        path = os.path.join(FONTS_DIR, name)
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    raise FileNotFoundError(f"No suitable font found for language={language}")

# Auto font scaling
def auto_scale_font(title: str, draw, max_width: int, language: str,
                    max_size: int = 80, min_size: int = 32) -> tuple:
    """Title যেন max_width-এ fit করে সেই অনুযায়ী font size কমায়।"""
    for size in range(max_size, min_size - 1, -4):
        font  = _best_font(True, size, language)
        lines = wrap_text(title, font, max_width, draw)
        if len(lines) <= 4:
            return font, lines
    font  = _best_font(True, min_size, language)
    lines = wrap_text(title, font, max_width, draw)
    return font, lines

# Text wrap
def wrap_text(text: str, font, max_width: int, draw) -> list[str]:
    words, lines, current = text.split(), [], ""
    for word in words:
        test = f"{current} {word}".strip()
        if draw.textbbox((0, 0), test, font=font)[2] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [text]

# Main
def create_image(
    title:       str,
    topic:       str = "",
    language:    str = "bn",
    output_path: str = "post.png",
) -> str:
    # Theme detection: topic + title
    theme    = detect_theme((topic or "") + " " + title)
    IMG_SIZE = 1024
    PADDING  = 80

    img  = Image.new("RGB", (IMG_SIZE, IMG_SIZE), theme["bg"])
    draw = ImageDraw.Draw(img)

    max_text_w = IMG_SIZE - PADDING * 2

    # Auto-scaled title font
    title_font, lines = auto_scale_font(title, draw, max_text_w, language)
    line_h   = int(title_font.size * 1.30)
    LINE_GAP = 38
    SUB_GAP  = 26

    sub_font  = _best_font(False, 36, language)
    name_font = _best_font(True,  30, language)
    role_font = _best_font(False, 25, language)

    # Vertical centering
    total_h = len(lines) * line_h + LINE_GAP + 3 + SUB_GAP + 48
    y       = (IMG_SIZE - total_h) // 2

    for line in lines:
        w = draw.textbbox((0, 0), line, font=title_font)[2]
        draw.text(((IMG_SIZE - w) / 2, y), line, fill="white", font=title_font)
        y += line_h

    # Decorative line
    line_y = y + LINE_GAP
    lx1    = IMG_SIZE // 2 - 200
    lx2    = IMG_SIZE // 2 + 200
    draw.line((lx1, line_y, lx2, line_y), fill=theme["accent"], width=3)

    # Subtitle
    sub = "(See caption for details...)" if language == "en" else "(বিস্তারিত ক্যাপশনে...)"
    sw  = draw.textbbox((0, 0), sub, font=sub_font)[2]
    draw.text(((IMG_SIZE - sw) / 2, line_y + SUB_GAP), sub, fill="#cbd5e1", font=sub_font)

    # Bottom-left branding
    MX, MY = 54, 54
    name_h = draw.textbbox((0, 0), "Rahat Ahmed",  font=name_font)[3]
    role_h = draw.textbbox((0, 0), "Admin, TechX", font=role_font)[3]
    role_y = IMG_SIZE - MY - role_h
    name_y = role_y - name_h - 8

    draw.text((MX, name_y), "Rahat Ahmed",  fill="white",   font=name_font)
    draw.text((MX, role_y), "Admin, TechX", fill="#94a3b8", font=role_font)

    img.save(output_path)
    return output_path