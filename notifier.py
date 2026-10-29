"""Persist digests locally and optionally send them to Telegram."""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

import requests

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

LOGGER = logging.getLogger(__name__)
DIGESTS_DIRECTORY = Path(__file__).resolve().parent / "digests"
TELEGRAM_API_BASE_URL = "https://api.telegram.org"
TELEGRAM_TIMEOUT_SECONDS = 20
TELEGRAM_MAX_MESSAGE_LENGTH = 4000


def save_digest(markdown_text: str) -> Path:
    """Save a digest as digests/YYYY-MM-DD.md and return its path."""
    if not markdown_text.strip():
        raise ValueError("Digest text must not be empty")

    DIGESTS_DIRECTORY.mkdir(parents=True, exist_ok=True)
    destination = DIGESTS_DIRECTORY / f"{date.today().isoformat()}.md"
    destination.write_text(markdown_text.rstrip() + "\n", encoding="utf-8")
    return destination


def split_message(
    message: str, max_chars: int = TELEGRAM_MAX_MESSAGE_LENGTH
) -> list[str]:
    """Split text into bounded chunks, preferring line and word boundaries."""
    if max_chars < 1:
        raise ValueError("max_chars must be a positive integer")
    if not message:
        return []

    chunks: list[str] = []
    remaining = message
    while len(remaining) > max_chars:
        boundary = remaining.rfind("\n", 0, max_chars)
        if boundary <= 0:
            boundary = remaining.rfind(" ", 0, max_chars)
        if boundary <= 0:
            boundary = max_chars
        else:
            boundary += 1
        chunks.append(remaining[:boundary])
        remaining = remaining[boundary:]
    if remaining:
        chunks.append(remaining)
    return chunks


def send_telegram(markdown_text: str) -> bool:
    """Send a digest in Telegram-safe chunks; return False when not configured."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        LOGGER.info("Telegram credentials are missing; skipping notification")
        return False
    if not markdown_text.strip():
        raise ValueError("Digest text must not be empty")

    endpoint = f"{TELEGRAM_API_BASE_URL}/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    for chunk in split_message(markdown_text):
        response = requests.post(
            endpoint,
            data={"chat_id": TELEGRAM_CHAT_ID, "text": chunk},
            timeout=TELEGRAM_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        result = response.json()
        if not result.get("ok"):
            raise RuntimeError(
                f"Telegram rejected a digest message: {result.get('description', 'unknown error')}"
            )
    return True
