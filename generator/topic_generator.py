import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# CONFIGURATION
# ============================================================

API_KEY = os.getenv("OPENROUTER_API_KEY")

MODEL = "openrouter/free"

PROMPTS_DIR = Path("prompts")
HISTORY_FILE = Path("topic_history.json")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

TOTAL_TOPICS = 24
MAX_HISTORY = 500


# ============================================================
# VALIDATE API KEY
# ============================================================

if not API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY is missing.")


# ============================================================
# LOAD TOPIC HISTORY
# ============================================================

def load_history():

    if not HISTORY_FILE.exists():
        return []

    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)

        if isinstance(history, list):
            return history

    except Exception:
        print("Warning: Could not read topic_history.json.")

    return []


# ============================================================
# SAVE TOPIC HISTORY
# ============================================================

def save_history(history):

    history = history[-MAX_HISTORY:]

    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(
            history,
            f,
            indent=2,
            ensure_ascii=False
        )


# ============================================================
# CLEAN MODEL RESPONSE
# ============================================================

def clean_response(content):

    content = content.strip()

    # Remove markdown code fences if model adds them
    if content.startswith("```"):
        lines = content.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        content = "\n".join(lines).strip()

    return content


# ============================================================
# REQUEST TOPICS FROM OPENROUTER
# ============================================================

def request_topics(history):

    previous_topics = history[-200:]

    history_text = json.dumps(
        previous_topics,
        ensure_ascii=False
    )

    system_prompt = """
You are an expert AI content strategist creating concepts for a
general-audience AI art Instagram account.

Generate exactly 24 UNIQUE visual concepts.

The audience includes:
- children
- teenagers
- young adults
- parents
- adults
- older people

The concepts should create strong curiosity, emotion, nostalgia,
wonder, beauty, surprise, or a "wow" reaction.

IMPORTANT:
- Every concept must work as a SINGLE AI-generated image.
- Do not create stories requiring multiple images.
- Do not depend on animation or video.
- Do not use copyrighted characters.
- Do not use real people's names.
- Do not use political content.
- Do not use disturbing/gory content.
- Do not use sexual content.
- Do not include text inside the generated image.
- Do not include logos or watermarks.
- Avoid repetitive ideas.
- Prefer visually spectacular and highly shareable concepts.
- Mix fantasy, nature, futuristic worlds, nostalgia, science,
  architecture, animals, culture-inspired environments,
  imaginative objects, emotional scenes, and impossible worlds.
- Make every idea visually different.

Each topic MUST contain:

id
name
description
prompt
caption
hashtags

The image prompt must be detailed enough for an image-generation
model.

The caption should be engaging and suitable for Instagram.

Hashtags must be an array of strings beginning with #.

Return ONLY valid JSON.

The JSON structure MUST be:

{
  "topics": [
    {
      "id": 1,
      "name": "...",
      "description": "...",
      "prompt": "...",
      "caption": "...",
      "hashtags": ["#...", "#..."]
    }
  ]
}

There must be exactly 24 objects in the topics array.
"""


    user_prompt = f"""
Create 24 fresh topics.

Previously used topic names are provided below.
DO NOT repeat or closely copy them.

Previous topics:
{history_text}

Return ONLY valid JSON.
"""


    payload = {
        "model": MODEL,

        "response_format": {
            "type": "json_object"
        },

        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],

        "temperature": 0.9,

        "max_tokens": 12000
    }


    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }


    print("Sending request to OpenRouter...")

    response = requests.post(
        OPENROUTER_URL,
        headers=headers,
        json=payload,
        timeout=180
    )

    print("OpenRouter status:", response.status_code)

    if response.status_code != 200:
        print(response.text)
        raise RuntimeError(
            f"OpenRouter request failed: HTTP {response.status_code}"
        )


    result = response.json()


    try:
        content = result["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        print(json.dumps(result, indent=2, ensure_ascii=False))
        raise RuntimeError(
            "Could not extract model response from OpenRouter."
        )


    return clean_response(content)


# ============================================================
# PARSE JSON WITH RETRY
# ============================================================

def generate_topics():

    print("Generating today's 24 topics...")

    history = load_history()

    max_attempts = 3

    for attempt in range(1, max_attempts + 1):

        print(f"Attempt {attempt}/{max_attempts}")

        try:

            content = request_topics(history)

            try:

                data = json.loads(content)

            except json.JSONDecodeError as e:

                print("Invalid JSON received from OpenRouter.")
                print("JSON error:", e)

                print("\nResponse preview:")
                print(content[:3000])

                if attempt == max_attempts:
                    raise RuntimeError(
                        "OpenRouter repeatedly returned invalid JSON."
                    )

                continue


            # =================================================
            # VALIDATE STRUCTURE
            # =================================================

            if not isinstance(data, dict):
                raise RuntimeError(
                    "OpenRouter response is not a JSON object."
                )


            topics = data.get("topics")


            if not isinstance(topics, list):
                raise RuntimeError(
                    "Response does not contain a 'topics' array."
                )


            if len(topics) != TOTAL_TOPICS:

                print(
                    f"Expected {TOTAL_TOPICS} topics, "
                    f"but received {len(topics)}."
                )

                if attempt == max_attempts:
                    raise RuntimeError(
                        f"Expected {TOTAL_TOPICS} topics, "
                        f"received {len(topics)}."
                    )

                continue


            # =================================================
            # VALIDATE EACH TOPIC
            # =================================================

            required_fields = [
                "id",
                "name",
                "description",
                "prompt",
                "caption",
                "hashtags"
            ]


            valid = True


            for index, topic in enumerate(topics, start=1):

                if not isinstance(topic, dict):

                    print(
                        f"Topic {index} is not an object."
                    )

                    valid = False
                    break


                for field in required_fields:

                    if field not in topic:

                        print(
                            f"Topic {index} missing field: {field}"
                        )

                        valid = False
                        break


                if not valid:
                    break


                if not isinstance(topic["hashtags"], list):

                    print(
                        f"Topic {index} hashtags must be an array."
                    )

                    valid = False
                    break


            if not valid:

                if attempt == max_attempts:
                    raise RuntimeError(
                        "Generated topics failed validation."
                    )

                continue


            # =================================================
            # REMOVE OLD JSON QUEUE
            # =================================================

            PROMPTS_DIR.mkdir(
                parents=True,
                exist_ok=True
            )


            for old_file in PROMPTS_DIR.glob("*.json"):

                old_file.unlink()


            # =================================================
            # SAVE 24 JSON FILES
            # =================================================

            new_history = list(history)

            for index, topic in enumerate(topics, start=1):

                topic["id"] = index

                filename = (
                    PROMPTS_DIR /
                    f"{index:02d}.json"
                )


                with open(
                    filename,
                    "w",
                    encoding="utf-8"
                ) as f:

                    json.dump(
                        topic,
                        f,
                        indent=2,
                        ensure_ascii=False
                    )


                print(
                    f"Created: {filename}"
                )


                new_history.append(
                    topic["name"]
                )


            # =================================================
            # SAVE HISTORY
            # =================================================

            save_history(new_history)


            print()
            print("=" * 60)
            print("SUCCESS")
            print(f"Created {TOTAL_TOPICS} topic JSON files.")
            print("=" * 60)

            return


        except Exception as e:

            print()
            print("Generation attempt failed:")
            print(str(e))
            print()

            if attempt == max_attempts:
                raise


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    generate_topics()
