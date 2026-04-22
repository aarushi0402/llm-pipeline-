"""
llm_client.py — Call Groq API with retry logic and structured JSON output
"""

import os
import json
import logging
import time
import re
from groq import Groq, APIStatusError, APITimeoutError, RateLimitError

logger = logging.getLogger(__name__)

# Load API key from environment
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise EnvironmentError("GROQ_API_KEY environment variable is not set.")

client = Groq(api_key=GROQ_API_KEY)

MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are a precise text analysis assistant. 
When given a passage of text, you MUST respond with ONLY a valid JSON object — no explanation, no markdown, no code fences.

The JSON must have exactly these keys:
{
  "summary": "2-3 sentence summary of the text",
  "entities": {
    "people": ["name1", "name2"],
    "places": ["place1"],
    "organizations": ["org1"]
  },
  "sentiment": {
    "label": "positive" | "neutral" | "negative",
    "confidence": 0.0 to 1.0
  },
  "key_questions": ["question1", "question2", "question3"]
}

Rules:
- summary must be 2-3 sentences
- entities lists can be empty if none found
- sentiment.confidence must be a float between 0.0 and 1.0
- key_questions must have exactly 3 questions
- Output ONLY the JSON. No extra text whatsoever."""

USER_PROMPT_TEMPLATE = """Analyze the following text and return only the JSON object as specified:

---
{text}
---"""


def extract_json(raw: str) -> dict:
    """
    Robustly extract a JSON object from LLM output,
    even if it contains markdown fences or extra text.
    """
    # Try direct parse first
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        pass

    # Try stripping markdown code fences
    cleaned = re.sub(r"```(?:json)?", "", raw).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Try finding the first {...} block
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse JSON from LLM response: {raw[:300]}")


def validate_result(data: dict) -> dict:
    """Fill in any missing keys with defaults so downstream code never breaks."""
    data.setdefault("summary", "No summary available.")
    data.setdefault("entities", {})
    data["entities"].setdefault("people", [])
    data["entities"].setdefault("places", [])
    data["entities"].setdefault("organizations", [])
    data.setdefault("sentiment", {"label": "neutral", "confidence": 0.0})
    data["sentiment"].setdefault("label", "neutral")
    data["sentiment"].setdefault("confidence", 0.0)
    data.setdefault("key_questions", ["N/A", "N/A", "N/A"])

    # Ensure exactly 3 questions
    qs = data["key_questions"]
    while len(qs) < 3:
        qs.append("N/A")
    data["key_questions"] = qs[:3]

    return data


def analyze_chunk(text: str, source: str = "", chunk_index: int = 0) -> dict | None:
    """
    Send a text chunk to Groq and return structured analysis.
    Retries up to 4 times with exponential backoff.
    """
    max_retries = 4
    base_delay = 2  # seconds

    for attempt in range(1, max_retries + 1):
        try:
            logger.debug(f"Calling Groq API (attempt {attempt}) for '{source}' chunk {chunk_index}")
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": USER_PROMPT_TEMPLATE.format(text=text)},
                ],
                temperature=0.2,
                max_tokens=800,
                timeout=30,
            )

            raw_output = response.choices[0].message.content
            parsed = extract_json(raw_output)
            validated = validate_result(parsed)

            # Attach metadata
            validated["source"] = source
            validated["chunk_index"] = chunk_index
            validated["chunk_text"] = text[:500]  # store first 500 chars for reference

            return validated

        except RateLimitError as e:
            wait = base_delay * (2 ** attempt)
            logger.warning(f"Rate limit hit on attempt {attempt}. Waiting {wait}s... ({e})")
            time.sleep(wait)

        except APITimeoutError as e:
            wait = base_delay * (2 ** attempt)
            logger.warning(f"Timeout on attempt {attempt}. Waiting {wait}s... ({e})")
            time.sleep(wait)

        except APIStatusError as e:
            if e.status_code in (500, 502, 503):
                wait = base_delay * (2 ** attempt)
                logger.warning(f"Server error {e.status_code} on attempt {attempt}. Waiting {wait}s...")
                time.sleep(wait)
            else:
                logger.error(f"Unrecoverable API error for '{source}' chunk {chunk_index}: {e}")
                return None

        except ValueError as e:
            logger.error(f"JSON parsing failed for '{source}' chunk {chunk_index}: {e}")
            return None

        except Exception as e:
            logger.error(f"Unexpected error for '{source}' chunk {chunk_index}: {e}")
            return None

    logger.error(f"All {max_retries} attempts failed for '{source}' chunk {chunk_index}. Skipping.")
    return None
