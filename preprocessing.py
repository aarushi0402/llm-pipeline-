"""
preprocessing.py — Clean text and split into LLM-friendly chunks
"""

import re
import logging

logger = logging.getLogger(__name__)

# Max tokens per chunk (conservative for Groq's context window)
MAX_CHUNK_TOKENS = 1500
# Rough approximation: 1 token ≈ 4 characters
CHARS_PER_TOKEN = 4
MAX_CHUNK_CHARS = MAX_CHUNK_TOKENS * CHARS_PER_TOKEN


def clean_text(text: str) -> str:
    """Fix encoding noise, collapse whitespace, remove boilerplate patterns."""
    # Fix common encoding artifacts
    text = text.encode("utf-8", errors="replace").decode("utf-8")

    # Remove non-printable characters (except newlines/tabs)
    text = re.sub(r"[^\x09\x0A\x0D\x20-\x7E\u00A0-\uFFFF]", " ", text)

    # Collapse excessive whitespace/blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)

    # Remove common boilerplate patterns
    boilerplate_patterns = [
        r"cookie policy.*?\n",
        r"accept all cookies.*?\n",
        r"subscribe to our newsletter.*?\n",
        r"all rights reserved.*?\n",
        r"privacy policy.*?\n",
        r"terms of (service|use).*?\n",
        r"advertisement\n",
        r"click here.*?\n",
    ]
    for pattern in boilerplate_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    return text.strip()


def split_into_chunks(text: str) -> list[str]:
    """
    Split text into chunks that fit within LLM token limits.
    Tries to split on paragraph boundaries first, then sentences.
    """
    if len(text) <= MAX_CHUNK_CHARS:
        return [text]

    chunks = []
    # Split by paragraphs first
    paragraphs = re.split(r"\n\n+", text)

    current_chunk = ""
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # If a single paragraph is too big, split it by sentences
        if len(para) > MAX_CHUNK_CHARS:
            sentences = re.split(r"(?<=[.!?])\s+", para)
            for sentence in sentences:
                if len(current_chunk) + len(sentence) + 1 <= MAX_CHUNK_CHARS:
                    current_chunk += (" " if current_chunk else "") + sentence
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = sentence
        else:
            if len(current_chunk) + len(para) + 2 <= MAX_CHUNK_CHARS:
                current_chunk += ("\n\n" if current_chunk else "") + para
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks if chunks else [text[:MAX_CHUNK_CHARS]]


def preprocess_and_chunk(raw_text: str, source: str = "") -> list[str]:
    """Clean text and return a list of chunks ready for LLM analysis."""
    logger.info(f"Preprocessing text from '{source}' ({len(raw_text)} chars)")
    cleaned = clean_text(raw_text)

    if not cleaned:
        raise ValueError(f"No usable text after cleaning from source: '{source}'")

    chunks = split_into_chunks(cleaned)
    logger.info(f"Created {len(chunks)} chunk(s) from '{source}'")
    return chunks
