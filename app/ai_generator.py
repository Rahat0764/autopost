import requests
import random
from config import GROQ_API_KEY

def generate_post(topic):
    hooks = [
        "এই ভুলটা করলে ক্যারিয়ার আটকে যাবে",
        "এই skill টা না জানলে পিছিয়ে পড়বে",
        "Senior developer হতে চাইলে এটা বুঝতেই হবে"
    ]

    hook = random.choice(hooks)

    prompt = f"""
    তুমি একজন experienced software engineer।

    Topic: {topic}

    লিখো:
    - Hook: {hook}
    - বাস্তব উদাহরণ
    - practical solution
    - actionable advice
    - শেষে CTA

    tone: human, professional, tech
    """

    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "llama3-70b-8192",
        "messages": [{"role": "user", "content": prompt}]
    }

    res = requests.post(url, json=data, headers=headers)

    return res.json()["choices"][0]["message"]["content"]