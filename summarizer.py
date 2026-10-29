"""Create a Markdown digest using Google's Gemini API."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Mapping, Sequence

import httpx
from google import genai
from google.genai.errors import APIError

from config import GOOGLE_API_KEY

LOGGER = logging.getLogger(__name__)
MODEL_NAME = "gemini-3.8-flash"
MAX_ATTEMPTS = 3


def summarize_digest(
    research_data: Mapping[str, Any], topics: Sequence[str]
) -> str:
    """Summarize research data into a readable, structured Markdown digest."""
    if not GOOGLE_API_KEY:
        raise RuntimeError(
            "GOOGLE_API_KEY is not configured; set it in the environment or .env file"
        )

    serialized_research = json.dumps(research_data, ensure_ascii=False, indent=2)
    topic_list = ", ".join(topic.strip() for topic in topics if topic.strip())
    prompt = f"""Create a concise daily technology digest in Markdown for these topics: {topic_list}.

Use only the supplied research data. Do not invent details or claim a source says
something that is not present. Organize the digest with a title, a short
executive summary, and sections for Hacker News and arXiv research. For each
selected item, include its title, a factual one- or two-sentence summary, and
the source link. If a section has no items, say so plainly.

Research data:
{serialized_research}
"""
    client = genai.Client(api_key=GOOGLE_API_KEY)

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
            )
            text = response.text
            if not text or not text.strip():
                raise RuntimeError("Gemini returned an empty digest")
            return text.strip()
        except (httpx.TimeoutException, TimeoutError) as exc:
            if attempt == MAX_ATTEMPTS:
                raise RuntimeError(
                    f"Gemini request timed out after {MAX_ATTEMPTS} attempts"
                ) from exc
            LOGGER.warning("Gemini request timed out; retrying (attempt %d)", attempt)
        except APIError as exc:
            status_code = exc.code
            retryable = status_code == 429 or (
                isinstance(status_code, int) and 500 <= status_code < 600
            )
            if not retryable or attempt == MAX_ATTEMPTS:
                raise RuntimeError(
                    f"Gemini API request failed (HTTP {status_code}): {exc}"
                ) from exc
            LOGGER.warning(
                "Gemini API returned HTTP %s; retrying (attempt %d)",
                status_code,
                attempt,
            )

        time.sleep(2 ** (attempt - 1))

    raise RuntimeError("Gemini request failed unexpectedly")
