"""
ingestion.py — Load raw text from .txt/.pdf files or URLs
"""

import logging
import requests
from pathlib import Path
from bs4 import BeautifulSoup
import pypdf

logger = logging.getLogger(__name__)


def load_file(path: str) -> str:
    """Load text from a .txt or .pdf file."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")

    suffix = p.suffix.lower()

    if suffix == ".txt":
        logger.info(f"Reading text file: {path}")
        return p.read_text(encoding="utf-8", errors="replace")

    elif suffix == ".pdf":
        logger.info(f"Reading PDF file: {path}")
        text_parts = []
        with open(p, "rb") as f:
            reader = pypdf.PdfReader(f)
            for page_num, page in enumerate(reader.pages):
                text = page.extract_text()
                if text:
                    text_parts.append(text)
                else:
                    logger.warning(f"Page {page_num+1} of '{path}' had no extractable text.")
        if not text_parts:
            raise ValueError(f"No text could be extracted from PDF: {path}")
        return "\n".join(text_parts)

    else:
        raise ValueError(f"Unsupported file type '{suffix}'. Only .txt and .pdf are supported.")


def load_url(url: str) -> str:
    """Scrape and return clean text from a URL."""
    logger.info(f"Fetching URL: {url}")
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        raise RuntimeError(f"Request timed out for URL: {url}")
    except requests.exceptions.HTTPError as e:
        raise RuntimeError(f"HTTP error {e.response.status_code} for URL: {url}")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Failed to fetch URL '{url}': {e}")

    soup = BeautifulSoup(response.text, "html.parser")

    # Remove boilerplate tags
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form", "noscript"]):
        tag.decompose()

    # Extract meaningful text
    text = soup.get_text(separator="\n")
    return text
