import requests
import os

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

def handler(request):
    try:
        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/posts?select=*",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}"
            }
        )

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json; charset=utf-8"
            },
            "body": res.text   # <-- IMPORTANT (json.dumps না)
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": '{"error": "' + str(e) + '"}'
        }