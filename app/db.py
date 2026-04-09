import requests
from config import SUPABASE_URL, SUPABASE_KEY

def save_log(topic, status):
    url = f"{SUPABASE_URL}/rest/v1/posts"

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "topic": topic,
        "status": status
    }

    requests.post(url, json=data, headers=headers)