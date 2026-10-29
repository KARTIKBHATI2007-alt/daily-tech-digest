"""Fetch technology news and recent research papers."""

from __future__ import annotations

import re
from html import unescape
from html.parser import HTMLParser
from typing import Any, Sequence

import feedparser
import requests

HACKER_NEWS_RSS_URL = "https://news.ycombinator.com/rss"
ARXIV_API_URL = "https://export.arxiv.org/api/query"
REQUEST_TIMEOUT_SECONDS = 20


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _clean_text(value: str) -> str:
    extractor = _HTMLTextExtractor()
    extractor.feed(value)
    text = unescape(" ".join(extractor.parts))
    return re.sub(r"\s+", " ", text).strip()


def _positive_limit(limit: int) -> int:
    if limit < 1:
        raise ValueError("limit must be a positive integer")
    return limit


def fetch_hacker_news(limit: int = 10) -> list[dict[str, str]]:
    """Fetch the latest Hacker News RSS entries."""
    limit = _positive_limit(limit)
    response = requests.get(HACKER_NEWS_RSS_URL, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    feed = feedparser.parse(response.content)
    if feed.bozo:
        raise ValueError(f"Unable to parse Hacker News RSS feed: {feed.bozo_exception}")

    stories: list[dict[str, str]] = []
    for entry in feed.entries[:limit]:
        title = _clean_text(str(entry.get("title", "")))
        link = str(entry.get("link", "")).strip()
        description = _clean_text(
            str(entry.get("summary", entry.get("description", "")))
        )
        if title and link:
            stories.append(
                {"title": title, "link": link, "summary": description}
            )
    return stories


def fetch_arxiv_papers(
    topics: Sequence[str], limit: int = 10
) -> list[dict[str, str]]:
    """Fetch recent arXiv papers matching one or more topic phrases."""
    limit = _positive_limit(limit)
    cleaned_topics = [topic.strip() for topic in topics if topic.strip()]
    if not cleaned_topics:
        raise ValueError("At least one non-empty topic is required")

    query_terms = []
    for topic in cleaned_topics:
        searchable_topic = topic.replace('"', "").replace("\\", "").strip()
        if searchable_topic:
            query_terms.append(f'all:"{searchable_topic}"')
    if not query_terms:
        raise ValueError("Topics must contain searchable text")
    response = requests.get(
        ARXIV_API_URL,
        params={
            "search_query": "(" + " OR ".join(query_terms) + ")",
            "start": 0,
            "max_results": limit,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    feed = feedparser.parse(response.content)
    if feed.bozo:
        raise ValueError(f"Unable to parse arXiv response: {feed.bozo_exception}")

    papers: list[dict[str, str]] = []
    for entry in feed.entries:
        title = _clean_text(str(entry.get("title", "")))
        link = str(entry.get("link", "")).strip()
        summary = _clean_text(str(entry.get("summary", "")))
        if title and link:
            papers.append({"title": title, "link": link, "summary": summary})
    return papers


def collect_research(
    topics: Sequence[str], hacker_news_limit: int = 10, arxiv_limit: int = 10
) -> dict[str, Any]:
    """Collect Hacker News stories and arXiv papers for the supplied topics."""
    cleaned_topics = [topic.strip() for topic in topics if topic.strip()]
    if not cleaned_topics:
        raise ValueError("At least one non-empty topic is required")
    return {
        "topics": cleaned_topics,
        "hacker_news": fetch_hacker_news(hacker_news_limit),
        "arxiv_papers": fetch_arxiv_papers(cleaned_topics, arxiv_limit),
    }
