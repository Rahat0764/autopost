import requests
from config import PAGE_ID, PAGE_ACCESS_TOKEN

def post_to_facebook(message, image_path):
    url = f"https://graph.facebook.com/v19.0/{PAGE_ID}/photos"

    with open(image_path, "rb") as img:
        res = requests.post(url,
            files={"source": img},
            data={
                "caption": message,
                "access_token": PAGE_ACCESS_TOKEN
            })

    return res.json()