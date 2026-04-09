import time, random
from ai_generator import generate_post
from image_maker import create_image
from poster import post_to_facebook
from telegram_alert import send_alert
from db import save_log

TOPICS = [
    "System Design interview",
    "Backend scaling",
    "API security",
    "Docker basics",
    "Microservices architecture"
]

used = []

def get_topic():
    global used
    if len(used) == len(TOPICS):
        used = []
    t = random.choice([x for x in TOPICS if x not in used])
    used.append(t)
    return t

def run():
    topic = get_topic()

    try:
        content = generate_post(topic)
        img = create_image(topic)

        res = post_to_facebook(content, img)

        if "id" in res:
            save_log(topic, "SUCCESS")
            send_alert(f"✅ {topic}")
        else:
            save_log(topic, "FAILED")
            send_alert(f"❌ {topic}")

    except Exception as e:
        send_alert(f"🚨 {str(e)}")

print("🚀 Running...")
while True:
    run()
    time.sleep(1200)
