import requests
import os
import json
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("❌ GROQ_API_KEY not set in environment variables")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"
TIMEOUT = 20

def _call_groq(system_prompt, user_prompt):
    """Low level Groq API caller"""

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    }

    res = requests.post(
        GROQ_URL,
        headers=headers,
        json=payload,
        timeout=TIMEOUT
    )

    if res.status_code != 200:
        raise RuntimeError(
            f"Groq API error {res.status_code}: {res.text}"
        )

    return res.json()["choices"][0]["message"]["content"]


# =================================================
# ENTITY EXTRACTION
# =================================================

@lru_cache(maxsize=1000)
def extract_metadata(text):
    """
    Extract:
    - title
    - entities
    - tags

    Returns dict
    """

    system_prompt = "You are a strict JSON metadata extraction engine. Return ONLY valid JSON without markdown formatting or code blocks."

    user_prompt = f"""
Extract:
1. short title
2. named entities
3. relevant tags

Return ONLY JSON.

Schema:
{{
  "title": "",
  "entities": [],
  "tags": []
}}

Text:
{text}
"""

    raw = _call_groq(system_prompt, user_prompt)

    # Strip markdown code fences if present
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]  # Get content between backticks
        if raw.startswith("json"):
            raw = raw[4:]  # Remove 'json' language identifier
    raw = raw.strip()

    try:
        data = json.loads(raw)

        return {
            "title": data.get("title", ""),
            "entities": data.get("entities", []),
            "tags": data.get("tags", [])
        }

    except json.JSONDecodeError:
        print("⚠️ Invalid JSON from Groq:", raw)

        return {
            "title": "",
            "entities": [],
            "tags": []
        }

@lru_cache(maxsize=1000)
def extract_entities(text):
    """
    Extract named entities using Groq
    Returns list[str]
    """

    system_prompt = "You are a strict JSON entity extraction engine. Return ONLY valid JSON without markdown formatting or code blocks."

    user_prompt = f"""
Extract named entities.

Return ONLY valid JSON array.

Schema:
["entity1", "entity2"]

Text:
{text}
"""

    raw = _call_groq(system_prompt, user_prompt)

    # Strip markdown code fences if present
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]  # Get content between backticks
        if raw.startswith("json"):
            raw = raw[4:]  # Remove 'json' language identifier
    raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        print("⚠️ Invalid JSON from Groq:", raw)
        return []


# =================================================
# QUICK TEST
# =================================================

if __name__ == "__main__":
    text = "Apple launched Vision Pro in California. Tim Cook presented it."

    print("\n🔹 ENTITIES")
    print(extract_entities(text))

    print("\n🔹 METADATA")
    print(extract_metadata(text))
