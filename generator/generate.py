import requests
import json
import os
import base64
import shutil
import subprocess
from pathlib import Path
from dotenv import load_dotenv

from instagram import publish_to_instagram


load_dotenv()


# ============================================================
# CONFIGURATION
# ============================================================

ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")

MODEL = "@cf/black-forest-labs/flux-2-klein-4b"

PROMPTS_DIR = Path("prompts")
OUTPUT_DIR = Path("output")
IMAGES_DIR = Path("images")

# GitHub Pages public URL
PUBLIC_IMAGE_BASE_URL = os.getenv(
    "PUBLIC_IMAGE_BASE_URL"
)

PROMPTS_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
IMAGES_DIR.mkdir(exist_ok=True)


# ============================================================
# CLOUDLFARE IMAGE GENERATION
# ============================================================

def generate_image(prompt, output_file):

    if not ACCOUNT_ID:
        raise RuntimeError(
            "CLOUDFLARE_ACCOUNT_ID is missing"
        )

    if not API_TOKEN:
        raise RuntimeError(
            "CLOUDFLARE_API_TOKEN is missing"
        )

    url = (
        f"https://api.cloudflare.com/client/v4/accounts/"
        f"{ACCOUNT_ID}/ai/run/{MODEL}"
    )

    headers = {
        "Authorization": f"Bearer {API_TOKEN}"
    }

    files = {
        "prompt": (None, prompt),
        "width": (None, "1024"),
        "height": (None, "1024")
    }

    print("Generating image with Cloudflare...")

    response = requests.post(
        url,
        headers=headers,
        files=files,
        timeout=300
    )

    print(
        "Cloudflare status:",
        response.status_code
    )

    if response.status_code != 200:
        print(response.text)
        return False

    result = response.json()

    try:
        image_base64 = result["result"]["image"]
    except KeyError:
        print("Unexpected Cloudflare response:")
        print(result)
        return False

    image_bytes = base64.b64decode(image_base64)

    with open(output_file, "wb") as f:
        f.write(image_bytes)

    print("Image saved:", output_file)

    return True


# ============================================================
# GITHUB
# ============================================================

def push_image_to_github(image_file):

    print("Pushing image to GitHub...")

    try:

        subprocess.run(
            [
                "git",
                "add",
                str(image_file)
            ],
            check=True
        )

        subprocess.run(
            [
                "git",
                "commit",
                "-m",
                f"Add {image_file.name}"
            ],
            check=True
        )

        subprocess.run(
            [
                "git",
                "push",
                "origin",
                "main"
            ],
            check=True
        )

        print("Image pushed to GitHub.")

        return True

    except subprocess.CalledProcessError as e:

        print("Git operation failed.")
        print(e)

        return False


# ============================================================
# MAIN HOURLY JOB
# ============================================================

def process_next_post():

    # --------------------------------------------------------
    # CHECK CONFIG
    # --------------------------------------------------------

    if not PUBLIC_IMAGE_BASE_URL:

        raise RuntimeError(
            "PUBLIC_IMAGE_BASE_URL is missing from .env"
        )

    # --------------------------------------------------------
    # FIND NEXT JSON
    # --------------------------------------------------------

    json_files = sorted(
        PROMPTS_DIR.glob("*.json")
    )

    if not json_files:

        print("No JSON files waiting.")
        return False

    json_file = json_files[0]

    print()
    print("=" * 60)
    print("NEXT POST")
    print("=" * 60)
    print("JSON:", json_file)

    # --------------------------------------------------------
    # READ JSON
    # --------------------------------------------------------

    with open(
        json_file,
        "r",
        encoding="utf-8"
    ) as f:

        data = json.load(f)

    post_id = int(data["id"])

    name = data["name"]

    prompt = data["prompt"]

    caption = data["caption"]

    hashtags = data["hashtags"]

    # --------------------------------------------------------
    # BUILD CAPTION
    # --------------------------------------------------------

    hashtag_text = " ".join(hashtags)

    full_caption = (
        f"{caption}\n\n"
        f"{hashtag_text}"
    )

    print("Topic:", name)

    # --------------------------------------------------------
    # IMAGE FILE
    # --------------------------------------------------------

    image_name = f"{post_id:02d}.png"

    output_file = (
        OUTPUT_DIR / image_name
    )

    github_image_file = (
        IMAGES_DIR / image_name
    )

    # --------------------------------------------------------
    # GENERATE IMAGE
    # --------------------------------------------------------

    success = generate_image(
        prompt,
        output_file
    )

    if not success:

        print(
            "Image generation failed."
        )

        print(
            "JSON kept for retry:"
            , json_file
        )

        return False

    # --------------------------------------------------------
    # COPY IMAGE TO PUBLIC GITHUB FOLDER
    # --------------------------------------------------------

    shutil.copy2(
        output_file,
        github_image_file
    )

    print(
        "Copied to:",
        github_image_file
    )

    # --------------------------------------------------------
    # PUSH TO GITHUB
    # --------------------------------------------------------

    success = push_image_to_github(
        github_image_file
    )

    if not success:

        print(
            "GitHub upload failed."
        )

        print(
            "JSON kept for retry."
        )

        return False

    # --------------------------------------------------------
    # PUBLIC IMAGE URL
    # --------------------------------------------------------

    image_url = (
        f"{PUBLIC_IMAGE_BASE_URL.rstrip('/')}/"
        f"{image_name}"
    )

    print()
    print("Public image URL:")
    print(image_url)

    # --------------------------------------------------------
    # INSTAGRAM
    # --------------------------------------------------------

    success = publish_to_instagram(
        image_url,
        full_caption
    )

    if not success:

        print()
        print(
            "Instagram publishing failed."
        )

        print(
            "JSON KEPT for retry:"
            , json_file
        )

        return False

    # --------------------------------------------------------
    # EVERYTHING SUCCESSFUL
    # --------------------------------------------------------

    json_file.unlink()

    print()
    print("=" * 60)
    print("POST COMPLETED SUCCESSFULLY")
    print("=" * 60)

    print("Instagram post:", name)
    print("JSON deleted:", json_file)
    print("Image:", output_file)

    return True


if __name__ == "__main__":
    success = process_next_post()

    if not success:
        raise SystemExit(1)
