import os
import json
from functools import lru_cache
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq()
MODEL = "llama-3.1-8b-instant"

def _call_groq(system_prompt, user_prompt):
    """Low level Groq API caller"""

    completion = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0,
        max_completion_tokens=8192,
        top_p=1
    )

    return completion.choices[0].message.content


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

    import time
    start = time.time()
    print("\n🔹 ENTITIES")
    print(extract_entities(text))
    end = time.time()
    print(f"⏱️ Extraction took {end - start:.2f} seconds")


    print("\n🔹 METADATA")
    print(extract_metadata(text))
