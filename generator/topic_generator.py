import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OPENROUTER_API_KEY")


MODEL = "openrouter/free"

OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "prompts"
)

# ============================================================
# OPENROUTER
# ============================================================

URL = "https://openrouter.ai/api/v1/chat/completions"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# ============================================================
# PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are a professional global trend researcher and creative director
for a highly visual Instagram account.

Your task is to create the BEST 24 image concepts for TODAY.

The content must NOT feel like a generic children's page.

The images should attract:

- children
- teenagers
- parents
- young adults
- general audiences

The goal is to create images that make people STOP SCROLLING.

The image should create feelings such as:

- WOW
- curiosity
- nostalgia
- wonder
- beauty
- mystery
- cuteness
- amazement
- imagination
- emotional connection

Think:

"I have never seen this before."

"That looks amazing."

"I want to see this."

"This reminds me of something from childhood."

"How did they make this?"

TREND RESEARCH:

Think about current global trends, emerging aesthetics,
seasonal interests, popular visual concepts, internet culture,
nature, wildlife, fascinating places, technology, science,
nostalgia, fantasy, architecture, food, travel and unusual
real-world phenomena.

Prioritize concepts that feel CURRENT and visually relevant.

Do not simply generate generic topics that have existed forever.

NOVELTY:

All 24 topics must be meaningfully different.

Do NOT create 24 variations of the same idea.

For example, these are NOT sufficiently different:

Tiny Forest Village
Tiny Jungle Village
Tiny Mountain Village
Tiny Beach Village

Instead, create genuinely different concepts.

REPETITION:

Avoid common repetitive concepts.

Every topic should feel fresh and interesting.

The topics should also be suitable for future daily generation,
so avoid using the exact same concepts repeatedly.

AUDIENCE:

The content must be family-friendly but NOT childish.

A child should enjoy it.

A parent should enjoy it.

A young adult should find it visually interesting.

The image should feel like premium social-media content.

VISUAL QUALITY:

Every topic must work as ONE powerful image.

Avoid ideas that require:

- dialogue
- multiple scenes
- long stories
- explanations
- text inside the image

IMAGE PROMPT:

For every topic create a detailed prompt suitable for an AI
image-generation model.

The prompt should describe:

- main subject
- environment
- composition
- camera viewpoint
- lighting
- atmosphere
- colors
- depth
- important visual details
- artistic or photographic style
- visual quality

The image should immediately look impressive in an Instagram feed.

Do NOT include:

- text
- captions
- logos
- watermarks
- written words

inside the generated image.

OUTPUT:

Return EXACTLY 24 objects.

Each object MUST have:

{
    "name": "short memorable topic name",
    "description": "short 1-2 sentence description",
    "prompt": "detailed image generation prompt"
}

Return ONLY valid JSON.

Do not use markdown.

Do not write anything before or after the JSON.

Make all 24 ideas feel like they were created by a
professional global visual-content creator.
"""

# ============================================================
# REQUEST
# ============================================================

DATA = {
    "model": MODEL,
    "messages": [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        },
        {
            "role": "user",
            "content": "Generate today's 24 image topics."
        }
    ],
    "temperature": 1.0
}

print("Generating 24 topics...")
print("Please wait...")

response = requests.post(
    URL,
    headers=HEADERS,
    json=DATA,
    timeout=180
)

# ============================================================
# CHECK RESPONSE
# ============================================================

print("Status:", response.status_code)

if response.status_code != 200:
    print("\nOpenRouter Error:")
    print(response.text)
    exit()

result = response.json()

content = result["choices"][0]["message"]["content"]

# Remove possible markdown fences
content = content.strip()

if content.startswith("```json"):
    content = content[7:]

if content.startswith("```"):
    content = content[3:]

if content.endswith("```"):
    content = content[:-3]

content = content.strip()

# ============================================================
# PARSE JSON
# ============================================================

try:
    topics = json.loads(content)
except json.JSONDecodeError as e:
    print("\nJSON parsing failed.")
    print("Error:", e)
    print("\nAI returned:")
    print(content)
    exit()

# ============================================================
# VALIDATE
# ============================================================

if not isinstance(topics, list):
    print("Error: AI response is not a JSON array.")
    exit()

if len(topics) != 24:
    print(f"Error: Expected 24 topics, received {len(topics)}.")
    exit()

for i, topic in enumerate(topics, start=1):

    required = ["name", "description", "prompt"]

    for field in required:
        if field not in topic:
            print(f"Error: Topic {i} is missing '{field}'.")
            exit()

# ============================================================
# CREATE OUTPUT DIRECTORY
# ============================================================

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================================================
# SAVE 24 JSON FILES
# ============================================================

for i, topic in enumerate(topics, start=1):

    file_path = os.path.join(
        OUTPUT_DIR,
        f"{i:02d}.json"
    )

    data = {
        "id": i,
        "name": topic["name"],
        "description": topic["description"],
        "prompt": topic["prompt"]
    }

    with open(
        file_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False
        )

# ============================================================
# SUCCESS
# ============================================================

print("\n========================================")
print("SUCCESS")
print("========================================")
print("24 topics generated successfully.")
print(f"Saved to: {OUTPUT_DIR}")
print("")

for i, topic in enumerate(topics, start=1):
    print(f"{i:02d}. {topic['name']}")