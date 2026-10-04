import requests
import os
import time
from dotenv import load_dotenv

load_dotenv()

ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
INSTAGRAM_USER_ID = os.getenv("INSTAGRAM_USER_ID")

GRAPH_URL = "https://graph.instagram.com/v25.0"


def publish_to_instagram(image_url, caption):

    if not ACCESS_TOKEN:
        raise RuntimeError(
            "INSTAGRAM_ACCESS_TOKEN is missing from .env"
        )

    if not INSTAGRAM_USER_ID:
        raise RuntimeError(
            "INSTAGRAM_USER_ID is missing from .env"
        )

    # --------------------------------------------------
    # STEP 1 — CREATE MEDIA CONTAINER
    # --------------------------------------------------

    print("Creating Instagram media container...")

    url = f"{GRAPH_URL}/{INSTAGRAM_USER_ID}/media"

    params = {
        "image_url": image_url,
        "caption": caption,
        "access_token": ACCESS_TOKEN
    }

    response = requests.post(
        url,
        params=params,
        timeout=60
    )

    print(
        "Container status:",
        response.status_code
    )

    if response.status_code != 200:
        print(response.text)
        return False

    result = response.json()

    creation_id = result.get("id")

    if not creation_id:
        print("No creation ID returned.")
        print(result)
        return False

    print("Creation ID:", creation_id)

    # --------------------------------------------------
    # STEP 2 — WAIT FOR INSTAGRAM PROCESSING
    # --------------------------------------------------

    print("Waiting for Instagram to process image...")

    for attempt in range(12):

        status_url = f"{GRAPH_URL}/{creation_id}"

        status_params = {
            "fields": "status_code",
            "access_token": ACCESS_TOKEN
        }

        status_response = requests.get(
            status_url,
            params=status_params,
            timeout=60
        )

        if status_response.status_code != 200:
            print(status_response.text)
            return False

        status_data = status_response.json()

        status = status_data.get("status_code")

        print(
            f"Processing check {attempt + 1}: {status}"
        )

        if status == "FINISHED":
            break

        if status in ["ERROR", "EXPIRED"]:
            print("Instagram processing failed.")
            print(status_data)
            return False

        time.sleep(5)

    else:
        print("Instagram processing timed out.")
        return False

    # --------------------------------------------------
    # STEP 3 — PUBLISH
    # --------------------------------------------------

    print("Publishing to Instagram...")

    publish_url = (
        f"{GRAPH_URL}/{INSTAGRAM_USER_ID}/media_publish"
    )

    publish_params = {
        "creation_id": creation_id,
        "access_token": ACCESS_TOKEN
    }

    publish_response = requests.post(
        publish_url,
        params=publish_params,
        timeout=60
    )

    print(
        "Publish status:",
        publish_response.status_code
    )

    if publish_response.status_code != 200:
        print(publish_response.text)
        return False

    publish_result = publish_response.json()

    print("Instagram published successfully!")
    print("Instagram media ID:", publish_result.get("id"))

    return True