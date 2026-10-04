import requests
import json
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OPENROUTER_API_KEY")

PROMPTS_DIR = Path("prompts")
HISTORY_FILE = Path("topic_history.json")

PROMPTS_DIR.mkdir(exist_ok=True)

MODEL = "openrouter/free"


SYSTEM_PROMPT = """
You are the content strategist for an Instagram AI-art account called
WonderCanvas.

Generate exactly 24 completely fresh image concepts for today's posts.

The audience is GENERAL:
- kids
- teenagers
- young adults
- parents
- adults
- AI-art lovers

Do NOT make the account mainly children's content.

The concepts should have strong:
- WOW effect
- curiosity
- emotional appeal
- nostalgia
- visual surprise
- scroll-stopping potential

Think about current visual trends, popular aesthetics, internet culture,
interesting science, fantasy, nature, futuristic concepts, surrealism,
nostalgia and visually unusual ideas.

Every concept must be suitable for ONE single Instagram image.

Avoid:
- repeated concepts
- boring generic landscapes
- text inside images
- logos
- watermarks
- brand names
- political content
- sexual content
- graphic gore

For each topic generate:

1. name
2. description
3. detailed image-generation prompt
4. Instagram caption
5. 6-12 hashtags

Captions should create curiosity and encourage comments/shares.

Return ONLY valid JSON.

Required format:

{
  "topics": [
    {
      "id": 1,
      "name": "...",
      "description": "...",
      "prompt": "...",
      "caption": "...",
      "hashtags": [
        "#AIArt",
        "#WonderCanvas"
      ]
    }
  ]
}
"""


def load_history():
    if not HISTORY_FILE.exists():
        return []

    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def generate_topics():

    if not API_KEY:
        raise RuntimeError(
            "OPENROUTER_API_KEY is missing from .env"
        )

    history = load_history()

    # Keep prompt size reasonable
    previous_topics = history[-200:]

    history_text = "\n".join(
        f"- {topic}"
        for topic in previous_topics
    )

    user_prompt = f"""
Generate today's 24 fresh WonderCanvas topics.

IMPORTANT:
Do NOT repeat or closely recreate any previous topic.

Previous topics:
{history_text}

Make today's concepts substantially different.

Return exactly 24 topics.
"""

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ]
    }

    print("Generating today's 24 topics...")

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=180
    )

    print("OpenRouter status:", response.status_code)

    if response.status_code != 200:
        print(response.text)
        raise RuntimeError("OpenRouter request failed")

    result = response.json()

    content = result["choices"][0]["message"]["content"].strip()

    # Remove markdown code fences if returned
    if content.startswith("```"):
        content = content.replace("```json", "")
        content = content.replace("```", "")
        content = content.strip()

    data = json.loads(content)

    topics = data["topics"]

    if len(topics) != 24:
        raise RuntimeError(
            f"Expected 24 topics, received {len(topics)}"
        )

    # Remove old unfinished queue
    for file in PROMPTS_DIR.glob("*.json"):
        file.unlink()

    today_names = []

    for index, topic in enumerate(topics, start=1):

        topic["id"] = index

        filename = PROMPTS_DIR / f"{index:02d}.json"

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(
                topic,
                f,
                indent=2,
                ensure_ascii=False
            )

        today_names.append(topic["name"])

        print(f"Created: {filename}")

    # Add today's topics to history
    history.extend(today_names)

    # Keep history manageable
    history = history[-500:]

    save_history(history)

    print()
    print("Successfully created 24 JSON files.")


if __name__ == "__main__":
    generate_topics()
