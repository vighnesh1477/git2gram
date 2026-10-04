import os
import json
import base64
import time
import shutil
import subprocess
from pathlib import Path

import requests
from dotenv import load_dotenv

from instagram import publish_to_instagram

load_dotenv()

CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
PUBLIC_IMAGE_BASE_URL = os.getenv(
    "PUBLIC_IMAGE_BASE_URL",
    "https://vighnesh1477.github.io/git2gram/images"
)

MODEL = "@cf/black-forest-labs/flux-2-klein-4b"

PROMPTS_DIR = Path("prompts")
OUTPUT_DIR = Path("output")
IMAGES_DIR = Path("images")

MAX_CLOUDFLARE_RETRIES = 3
CLOUDFLARE_TIMEOUT = 300
RETRY_WAIT = 15


if not CLOUDFLARE_API_TOKEN:
    raise RuntimeError("CLOUDFLARE_API_TOKEN is missing.")

if not CLOUDFLARE_ACCOUNT_ID:
    raise RuntimeError("CLOUDFLARE_ACCOUNT_ID is missing.")


OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
IMAGES_DIR.mkdir(parents=True, exist_ok=True)


def get_next_json():
    files = sorted(PROMPTS_DIR.glob("*.json"))

    if not files:
        return None

    return files[0]


def generate_image(prompt, output_path):

    url = (
        f"https://api.cloudflare.com/client/v4/accounts/"
        f"{CLOUDFLARE_ACCOUNT_ID}/ai/run/{MODEL}"
    )

    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}"
    }

    files = {
        "prompt": (None, prompt),
        "width": (None, "1024"),
        "height": (None, "1024")
    }

    for attempt in range(1, MAX_CLOUDFLARE_RETRIES + 1):

        print(f"\nCloudflare attempt {attempt}/{MAX_CLOUDFLARE_RETRIES}")

        try:

            response = requests.post(
                url,
                headers=headers,
                files=files,
                timeout=CLOUDFLARE_TIMEOUT
            )

            print("Cloudflare status:", response.status_code)

            if response.status_code == 200:

                data = response.json()

                if not data.get("success"):
                    print("Cloudflare returned success=false.")
                    print(json.dumps(data, indent=2))

                else:

                    result = data.get("result", {})
                    image_base64 = result.get("image")

                    if image_base64:

                        image_data = base64.b64decode(image_base64)

                        with open(output_path, "wb") as f:
                            f.write(image_data)

                        print("Image saved:", output_path)

                        return True

                    print("Cloudflare response did not contain an image.")
                    print(json.dumps(data, indent=2))

            elif response.status_code in [408, 429, 500, 502, 503, 504]:

                print("Temporary Cloudflare error.")
                print(response.text[:2000])

            else:

                print("Cloudflare request failed.")
                print(response.text[:3000])

                return False

        except requests.exceptions.Timeout:

            print("Cloudflare request timed out.")

        except requests.exceptions.RequestException as e:

            print("Cloudflare request error:", str(e))

        except Exception as e:

            print("Unexpected Cloudflare error:", str(e))

        if attempt < MAX_CLOUDFLARE_RETRIES:

            print(f"Waiting {RETRY_WAIT} seconds before retry...")
            time.sleep(RETRY_WAIT)

    print("Cloudflare image generation failed after all retries.")

    return False


def run_git(command):

    print("Running:", " ".join(command))

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.stdout:
        print(result.stdout)

    if result.stderr:
        print(result.stderr)

    return result.returncode == 0


def push_image_to_github(image_path):

    filename = image_path.name

    github_image = IMAGES_DIR / filename

    shutil.copy2(image_path, github_image)

    print("Copied to:", github_image)

    print("Pushing image to GitHub...")

    if not run_git(["git", "add", str(github_image)]):
        return False

    status = subprocess.run(
        ["git", "diff", "--cached", "--quiet"]
    )

    if status.returncode == 0:

        print("Image already exists in Git.")

        return True

    if not run_git(
        ["git", "commit", "-m", f"Add {filename}"]
    ):
        return False

    if not run_git(
        ["git", "push", "origin", "main"]
    ):
        return False

    print("Image pushed to GitHub.")

    return True


def wait_for_public_image(
    image_url,
    attempts=12,
    wait_seconds=10
):

    print("\nChecking public image URL:")
    print(image_url)

    for attempt in range(1, attempts + 1):

        print(f"Public URL check {attempt}/{attempts}")

        try:

            response = requests.get(
                image_url,
                timeout=30
            )

            print("HTTP status:", response.status_code)

            content_type = response.headers.get(
                "Content-Type",
                ""
            )

            print("Content-Type:", content_type)

            if (
                response.status_code == 200
                and content_type.startswith("image/")
            ):

                print("Public image is available.")

                return True

        except requests.RequestException as e:

            print(
                "Public URL check failed:",
                str(e)
            )

        if attempt < attempts:
            time.sleep(wait_seconds)

    print(
        "GitHub Pages image was not available in time."
    )

    return False


def delete_json_from_github(json_file):

    print("\nDeleting processed JSON from GitHub:")

    print(json_file)

    try:

        json_file.unlink()

    except Exception as e:

        print("Could not delete JSON:", str(e))

        return False

    print("JSON deleted locally.")

    if not run_git(
        ["git", "add", str(json_file)]
    ):
        return False

    status = subprocess.run(
        ["git", "diff", "--cached", "--quiet"]
    )

    if status.returncode == 0:

        print("No Git change detected.")

        return True

    if not run_git(
        [
            "git",
            "commit",
            "-m",
            f"Remove processed topic {json_file.name}"
        ]
    ):
        return False

    if not run_git(
        ["git", "push", "origin", "main"]
    ):
        return False

    print("JSON deletion pushed to GitHub.")

    return True


def process_next_post():

    json_file = get_next_json()

    if json_file is None:

        print("\nNo pending JSON files.")

        return True

    print("\n" + "=" * 60)
    print("NEXT POST")
    print("=" * 60)

    print("JSON:", json_file)

    try:

        with open(
            json_file,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

    except Exception as e:

        print("Could not read JSON:", str(e))

        return False

    topic_name = data.get(
        "name",
        "Untitled"
    )

    prompt = data.get("prompt")

    caption = data.get(
        "caption",
        ""
    )

    hashtags = data.get(
        "hashtags",
        []
    )

    if not prompt:

        print("Image prompt is missing.")

        return False

    if isinstance(hashtags, list):

        hashtag_text = " ".join(
            str(tag)
            for tag in hashtags
        )

    else:

        hashtag_text = str(hashtags)

    if hashtag_text:

        final_caption = (
            f"{caption}\n\n"
            f"{hashtag_text}"
        )

    else:

        final_caption = caption

    print("Topic:", topic_name)

    image_name = (
        json_file.stem +
        ".png"
    )

    output_path = (
        OUTPUT_DIR /
        image_name
    )

    print(
        "Generating image with Cloudflare..."
    )

    success = generate_image(
        prompt,
        output_path
    )

    if not success:

        print("Image generation failed.")

        print(
            f"JSON kept for retry: {json_file}"
        )

        return False

    if not push_image_to_github(
        output_path
    ):

        print("GitHub image push failed.")

        print(
            f"JSON kept for retry: {json_file}"
        )

        return False

    image_url = (
        f"{PUBLIC_IMAGE_BASE_URL}/"
        f"{image_name}"
    )

    print("\nPublic image URL:")
    print(image_url)

    if not wait_for_public_image(
        image_url
    ):

        print("Public image is not ready.")

        print(
            f"JSON kept for retry: {json_file}"
        )

        return False

    print(
        "\nCreating Instagram media container..."
    )

    instagram_success = publish_to_instagram(
        image_url,
        final_caption
    )

    if not instagram_success:

        print(
            "\nInstagram publishing failed."
        )

        print(
            f"JSON KEPT for retry: {json_file}"
        )

        return False

    print(
        "\nInstagram post published successfully."
    )

    if not delete_json_from_github(
        json_file
    ):

        print(
            "\nWARNING: Instagram succeeded, "
            "but JSON deletion was not pushed."
        )

        return False

    print("\n" + "=" * 60)
    print("POST COMPLETED SUCCESSFULLY")
    print("=" * 60)

    return True


if __name__ == "__main__":

    success = process_next_post()

    if not success:

        raise SystemExit(1)
