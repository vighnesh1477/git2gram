import os
import json
import base64
import requests
from dotenv import load_dotenv

# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")

# ============================================================
# CONFIGURATION
# ============================================================

MODEL = "@cf/black-forest-labs/flux-2-klein-4b"

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

PROMPTS_DIR = os.path.join(BASE_DIR, "prompts")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================================================
# FIND NEXT PROMPT
# ============================================================

json_files = [
    file for file in os.listdir(PROMPTS_DIR)
    if file.endswith(".json")
]

if not json_files:
    print("No prompt files found.")
    exit()

# Sort 01.json, 02.json, 03.json...
json_files.sort()

prompt_file = json_files[0]

prompt_path = os.path.join(
    PROMPTS_DIR,
    prompt_file
)

print(f"Using prompt file: {prompt_file}")

# ============================================================
# READ JSON
# ============================================================

with open(prompt_path, "r", encoding="utf-8") as file:
    prompt_data = json.load(file)

topic_name = prompt_data["name"]
description = prompt_data["description"]
prompt = prompt_data["prompt"]

print(f"Topic: {topic_name}")
print(f"Description: {description}")

# ============================================================
# OUTPUT FILE
# ============================================================

file_number = os.path.splitext(prompt_file)[0]

output_path = os.path.join(
    OUTPUT_DIR,
    f"{file_number}.png"
)

# ============================================================
# CLOUDFLARE API
# ============================================================

url = (
    f"https://api.cloudflare.com/client/v4/accounts/"
    f"{ACCOUNT_ID}/ai/run/{MODEL}"
)

headers = {
    "Authorization": f"Bearer {API_TOKEN}"
}

data = {
    "prompt": prompt,
    "width": 1024,
    "height": 1024
}

# ============================================================
# GENERATE IMAGE
# ============================================================

print("\nGenerating image...")
print("Please wait...")

response = requests.post(
    url,
    headers=headers,
    data=data,
    timeout=180
)

print("Status:", response.status_code)

# ============================================================
# HANDLE ERROR
# ============================================================

if response.status_code != 200:
    print("\nCloudflare Error:")
    print(response.text)

    print("\nPrompt file was NOT deleted.")
    print("It can be retried later.")

    exit()

# ============================================================
# GET IMAGE
# ============================================================

result = response.json()

image_base64 = result["result"]["image"]

image_data = base64.b64decode(image_base64)

# ============================================================
# SAVE IMAGE
# ============================================================

with open(output_path, "wb") as file:
    file.write(image_data)

print("\n========================================")
print("IMAGE GENERATED SUCCESSFULLY")
print("========================================")
print(f"Topic   : {topic_name}")
print(f"Prompt  : {prompt_file}")
print(f"Image   : {output_path}")

# ============================================================
# DELETE PROCESSED JSON
# ============================================================

os.remove(prompt_path)

print(f"Deleted : {prompt_file}")
print("========================================")