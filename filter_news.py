"""AI-news filtering and lightweight analytics."""

from __future__ import annotations

import logging
import re
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

LOGGER = logging.getLogger(__name__)

AI_KEYWORDS = [
    "ai",
    "artificial intelligence",
    "machine learning",
    "deep learning",
    "llm",
    "large language model",
    "generative ai",
    "genai",
    "chatgpt",
    "openai",
    "anthropic",
    "claude",
    "grok",
    "copilot",
    "nvidia",
    "neural",
    "transformer",
    "computer vision",
    "rag",
    "agentic",
    "multimodal",
]

CATEGORY_KEYWORDS = {
    "Model Releases": ["model", "launch", "release", "version", "benchmark"],
    "Regulation & Policy": ["regulation", "policy", "law", "government", "compliance"],
    "Funding & Business": ["funding", "acquisition", "startup", "revenue", "valuation"],
    "Research": ["research", "paper", "study", "university", "arxiv"],
    "Product & Integration": ["product", "feature", "integration", "workflow", "tool"],
}

STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "that",
    "this",
    "will",
    "into",
    "over",
    "after",
    "about",
    "have",
    "has",
    "are",
    "was",
    "its",
    "their",
    "new",
    "today",
    "says",
    "say",
}


def _text_blob(item: dict[str, Any]) -> str:
    return f"{item.get('title', '')} {item.get('snippet', '')}".lower()


def _matched_keywords(text: str) -> list[str]:
    matched = [k for k in AI_KEYWORDS if k in text]
    return sorted(set(matched))


def _classify_category(text: str) -> str:
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return category
    return "General AI News"


def filter_ai_news(news_items: list[dict[str, Any]], min_keyword_hits: int = 1) -> list[dict[str, Any]]:
    """Keep only AI-related news items using keyword scoring."""
    filtered: list[dict[str, Any]] = []
    for item in news_items:
        text = _text_blob(item)
        hits = _matched_keywords(text)
        if len(hits) < min_keyword_hits:
            continue
        enriched = dict(item)
        enriched["matched_keywords"] = ", ".join(hits)
        enriched["keyword_score"] = len(hits)
        enriched["category"] = _classify_category(text)
        filtered.append(enriched)

    LOGGER.info("Filtered %s AI-relevant articles from %s total.", len(filtered), len(news_items))
    return filtered


def save_news_to_csv(news_items: list[dict[str, Any]], csv_path: Path) -> None:
    """Append current run's articles to CSV storage."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    run_df = pd.DataFrame(news_items)
    if run_df.empty:
        LOGGER.warning("No items to save to CSV.")
        return

    if csv_path.exists():
        history_df = pd.read_csv(csv_path)
        combined = pd.concat([history_df, run_df], ignore_index=True)
        combined.drop_duplicates(subset=["link"], inplace=True)
    else:
        combined = run_df

    combined.to_csv(csv_path, index=False)
    LOGGER.info("Saved %s cumulative rows to %s", len(combined), csv_path)


def _extract_keywords(texts: list[str], top_n: int) -> list[tuple[str, int]]:
    counter: Counter[str] = Counter()
    for text in texts:
        tokens = re.findall(r"[a-zA-Z]{3,}", text.lower())
        for token in tokens:
            if token in STOPWORDS:
                continue
            counter[token] += 1
    return counter.most_common(top_n)


def analyze_news(news_items: list[dict[str, Any]], top_n_keywords: int = 10) -> dict[str, Any]:
    """Generate basic analytics for internship-friendly reporting."""
    if not news_items:
        return {
            "article_count": 0,
            "top_keywords": [],
            "source_distribution": {},
            "category_distribution": {},
        }

    titles_and_snippets = [_text_blob(item) for item in news_items]
    top_keywords = _extract_keywords(titles_and_snippets, top_n_keywords)
    source_distribution = dict(Counter(item.get("source", "Unknown") for item in news_items))
    category_distribution = dict(Counter(item.get("category", "General AI News") for item in news_items))

    analytics = {
        "article_count": len(news_items),
        "top_keywords": top_keywords,
        "source_distribution": source_distribution,
        "category_distribution": category_distribution,
    }
    LOGGER.info("Analytics prepared: %s", analytics)
    return analytics
