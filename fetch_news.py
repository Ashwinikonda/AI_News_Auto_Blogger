"""SerpAPI integration for fetching the latest AI news."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import requests

from config import Settings

LOGGER = logging.getLogger(__name__)
SERPAPI_ENDPOINT = "https://serpapi.com/search.json"


def _safe_get_source(item: dict[str, Any]) -> str:
    source = item.get("source")
    if isinstance(source, dict):
        return source.get("name") or source.get("title") or "Unknown"
    if isinstance(source, str):
        return source
    return "Unknown"


def _normalize_article(item: dict[str, Any], query_timestamp: str) -> dict[str, Any]:
    return {
        "title": (item.get("title") or "").strip(),
        "link": (item.get("link") or "").strip(),
        "source": _safe_get_source(item),
        "published_at": item.get("iso_date") or item.get("date") or "",
        "snippet": (item.get("snippet") or item.get("summary") or "").strip(),
        "position": item.get("position", 0),
        "fetched_at_utc": query_timestamp,
    }


def fetch_latest_news(settings: Settings) -> list[dict[str, Any]]:
    """Fetch latest news articles from SerpAPI Google News endpoint."""
    LOGGER.info("Fetching latest news from SerpAPI...")
    result_count = max(1, min(settings.news_results_limit, 100))
    params = {
        "engine": "google_news",
        "q": settings.news_query,
        "gl": settings.news_country,
        "hl": settings.news_language,
        "num": result_count,
        "no_cache": "true",
        "api_key": settings.serpapi_key,
    }
    response = requests.get(
        SERPAPI_ENDPOINT,
        params=params,
        timeout=settings.request_timeout_seconds,
    )
    if response.status_code >= 400:
        error_body = response.text[:600]
        raise requests.HTTPError(
            f"SerpAPI request failed with status {response.status_code}. "
            f"Response snippet: {error_body}",
            response=response,
        )
    payload = response.json()

    raw_items = payload.get("news_results", [])
    if not raw_items:
        raise ValueError("SerpAPI returned no news_results.")

    query_timestamp = datetime.now(timezone.utc).isoformat()
    normalized: list[dict[str, Any]] = []
    seen_links: set[str] = set()

    for item in raw_items:
        article = _normalize_article(item, query_timestamp)
        link = article["link"]
        if not article["title"] or not link:
            continue
        if link in seen_links:
            continue
        seen_links.add(link)
        normalized.append(article)

        # Include story variants if present.
        for story in item.get("stories", []) or []:
            story_article = _normalize_article(story, query_timestamp)
            story_link = story_article["link"]
            if not story_article["title"] or not story_link or story_link in seen_links:
                continue
            seen_links.add(story_link)
            normalized.append(story_article)

    if not normalized:
        raise ValueError("No valid news articles found after normalization.")

    LOGGER.info("Fetched %s normalized articles.", len(normalized))
    return normalized
