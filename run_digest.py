"""Command-line entry point for the Daily Tech Digest."""

from __future__ import annotations

import argparse
import logging
from typing import Any, Sequence

import requests
from notifier import save_digest, send_telegram
from researcher import collect_research
from summarizer import summarize_digest

LOGGER = logging.getLogger("daily_tech_digest")


def _fake_research(topics: Sequence[str]) -> dict[str, Any]:
    topic_summary = ", ".join(topics)
    return {
        "topics": list(topics),
        "hacker_news": [
            {
                "title": f"Example technology story for {topics[0]}",
                "link": "https://news.ycombinator.com/",
                "summary": "Sample data for testing the digest workflow without network access.",
            }
        ],
        "arxiv_papers": [
            {
                "title": f"Example research paper related to {topics[0]}",
                "link": "https://arxiv.org/",
                "summary": (
                    "Sample paper data for the requested topic set: "
                    f"{topic_summary}. No external service was contacted."
                ),
            }
        ],
    }


def _fake_digest(research_data: dict[str, Any], topics: Sequence[str]) -> str:
    story = research_data["hacker_news"][0]
    paper = research_data["arxiv_papers"][0]
    return (
        f"# Daily Tech Digest\n\n"
        f"**Topics:** {', '.join(topics)}\n\n"
        "## Hacker News\n\n"
        f"- [{story['title']}]({story['link']}) — {story['summary']}\n\n"
        "## arXiv Research\n\n"
        f"- [{paper['title']}]({paper['link']}) — {paper['summary']}\n"
    )


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch, summarize, save, and optionally deliver a daily tech digest."
    )
    parser.add_argument(
        "--topics",
        default="AI, Software Engineering",
        help='Comma-separated topics (default: "AI, Software Engineering")',
    )
    parser.add_argument(
        "--fake",
        action="store_true",
        help="Use offline sample data; save the digest without contacting Gemini or Telegram",
    )
    args = parser.parse_args(argv)
    args.topics = [topic.strip() for topic in args.topics.split(",") if topic.strip()]
    if not args.topics:
        parser.error("--topics must contain at least one non-empty topic")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = _parse_args(argv)
    try:
        if args.fake:
            research_data = _fake_research(args.topics)
            digest = _fake_digest(research_data, args.topics)
        else:
            research_data = collect_research(args.topics)
            digest = summarize_digest(research_data, args.topics)

        destination = save_digest(digest)
        LOGGER.info("Digest saved to %s", destination)
        if args.fake:
            LOGGER.info("Fake mode enabled; Telegram notification was skipped")
        else:
            sent = send_telegram(digest)
            if sent:
                LOGGER.info("Digest sent to Telegram")
        return 0
    except (OSError, requests.RequestException, RuntimeError, ValueError) as exc:
        LOGGER.error("Unable to create daily digest: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
