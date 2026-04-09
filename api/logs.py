import requests
import os

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

def handler(request):
    res = requests.get(
        f"{SUPABASE_URL}/rest/v1/posts?select=*",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}"
        }
    )

    return {
        "statusCode": 200,
        "body": res.text
    }
