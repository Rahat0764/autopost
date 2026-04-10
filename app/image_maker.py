from PIL import Image, ImageDraw, ImageFont
import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))


def wrap_text(text, font, max_width, draw):
    lines = []
    words = text.split()

    current_line = ""
    for word in words:
        test_line = current_line + " " + word if current_line else word
        w = draw.textbbox((0, 0), test_line, font=font)[2]

        if w <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    return lines


def create_image(title, output_path="post.png"):
    IMG_SIZE = 1024
    img = Image.new("RGB", (IMG_SIZE, IMG_SIZE), "#0a0f2c")
    draw = ImageDraw.Draw(img)

    title_font = ImageFont.truetype(
        os.path.join(BASE_DIR, "fonts/NotoSerifBengali-Bold.ttf"), 80
    )
    sub_font = ImageFont.truetype(
        os.path.join(BASE_DIR, "fonts/NotoSerifBengali-Regular.ttf"), 40
    )

    # Footer
    name_font = ImageFont.truetype(
        os.path.join(BASE_DIR, "fonts/NotoSerifBengali-Bold.ttf"), 32
    )
    role_font = ImageFont.truetype(
        os.path.join(BASE_DIR, "fonts/NotoSerifBengali-Regular.ttf"), 26
    )

    # Title wrap
    lines = wrap_text(title, title_font, 860, draw)
    line_height = 95

    total_title_height = len(lines) * line_height

    LINE_GAP = 40
    SUB_GAP = 28
    sub_height = 50

    total_block_height = total_title_height + LINE_GAP + 3 + SUB_GAP + sub_height
    y_start = (IMG_SIZE - total_block_height) // 2

    # Main title
    y = y_start
    for line in lines:
        w = draw.textbbox((0, 0), line, font=title_font)[2]
        draw.text(((IMG_SIZE - w) / 2, y), line, fill="white", font=title_font)
        y += line_height

    # Decorative line
    line_y = y + LINE_GAP
    draw.line((300, line_y, 724, line_y), fill="#00c6ff", width=3)

    # Subtitle
    subtitle = "(বিস্তারিত ক্যাপশনে...)"
    sw = draw.textbbox((0, 0), subtitle, font=sub_font)[2]
    draw.text(((IMG_SIZE - sw) / 2, line_y + SUB_GAP), subtitle, fill="#cbd5e1", font=sub_font)

    # Footer
    MARGIN_X = 54
    MARGIN_Y = 54

    name_text = "Rahat Ahmed"
    role_text = "Admin, TechX"

    name_h = draw.textbbox((0, 0), name_text, font=name_font)[3]
    role_h = draw.textbbox((0, 0), role_text, font=role_font)[3]

    # Role and Name position
    role_y = IMG_SIZE - MARGIN_Y - role_h
    name_y = role_y - name_h - 8

    draw.text((MARGIN_X, name_y), name_text, fill="white", font=name_font)
    draw.text((MARGIN_X, role_y), role_text, fill="#94a3b8", font=role_font)

    img.save(output_path)
    return output_path