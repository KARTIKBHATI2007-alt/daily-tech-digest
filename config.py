"""Application configuration loaded from environment variables."""

import os

from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY: str | None = os.getenv("GOOGLE_API_KEY")
TELEGRAM_BOT_TOKEN: str | None = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID: str | None = os.getenv("TELEGRAM_CHAT_ID")
