import os
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")

url = "https://graph.instagram.com/v25.0/me"

params = {
    "fields": "id,username",
    "access_token": TOKEN
}

response = requests.get(url, params=params)

print("Status:", response.status_code)
print(response.json())