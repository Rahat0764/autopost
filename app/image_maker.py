from PIL import Image, ImageDraw, ImageFont

def create_image(title, output_path="post.png"):
    img = Image.new("RGB", (1024, 1024), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    title_font = ImageFont.truetype("fonts/NotoSansBengali-Bold.ttf", 72)
    sub_font = ImageFont.truetype("fonts/NotoSansBengali-Regular.ttf", 36)

    draw.text((80, 350), title, fill=(0,0,0), font=title_font)
    draw.text((80, 520), "(বিস্তারিত ক্যাপশনে...)", fill=(120,120,120), font=sub_font)

    img.save(output_path)
    return output_path