"""Pipeline controller for AI News Auto-Blogger & Email Automation."""

from __future__ import annotations

import json
import logging
from dataclasses import replace
from pathlib import Path
from typing import Any

from blog_generator import build_blog_assets
from config import DATA_DIR, Settings, get_settings
from email_formatter import format_email_html
from email_sender import send_email
from fetch_news import fetch_latest_news
from filter_news import analyze_news, filter_ai_news, save_news_to_csv
from llm_service import GroqLLMService

LOGGER = logging.getLogger(__name__)


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def _is_rate_limit_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return "rate limit" in text or "429" in text or "too many requests" in text


def _build_fallback_summary(filtered_news: list[dict[str, Any]]) -> dict[str, Any]:
    top_items = filtered_news[:5]
    top_stories = []
    key_points = []
    for item in top_items:
        title = str(item.get("title", "")).strip()
        snippet = str(item.get("snippet", "")).strip()
        source = str(item.get("source", "")).strip()
        if title:
            top_stories.append(
                {
                    "title": title,
                    "source": source or "Unknown source",
                    "why_it_matters": snippet[:220] if snippet else "Emerging update in the AI ecosystem.",
                }
            )
            key_points.append(f"{title} ({source or 'Unknown source'})")

    executive_summary = (
        f"Compiled {len(filtered_news)} AI-related articles. "
        "This fallback summary was generated without LLM due to temporary API rate limits."
    )
    return {
        "executive_summary": executive_summary,
        "key_points": key_points[:5],
        "top_stories": top_stories,
    }


def _build_fallback_blog(summary_data: dict[str, Any], filtered_news: list[dict[str, Any]]) -> str:
    lines = [
        "# Daily AI News Brief",
        "",
        "## Executive Summary",
        str(summary_data.get("executive_summary", "AI news highlights for today.")),
        "",
        "## Key Developments",
    ]
    key_points = summary_data.get("key_points", [])
    if key_points:
        for point in key_points[:8]:
            lines.append(f"- {point}")
    else:
        lines.append("- Key points unavailable in fallback mode.")

    lines.extend(["", "## Top Articles"])
    for item in filtered_news[:10]:
        title = str(item.get("title", "")).strip() or "Untitled article"
        source = str(item.get("source", "")).strip() or "Unknown source"
        snippet = str(item.get("snippet", "")).strip()
        link = str(item.get("link", "")).strip()
        lines.append(f"### {title}")
        lines.append(f"Source: {source}")
        if snippet:
            lines.append("")
            lines.append(snippet[:350])
        if link:
            lines.append("")
            lines.append(f"[Read more]({link})")
        lines.append("")

    lines.extend(
        [
            "## Notes",
            "This edition used fallback generation because the LLM provider returned rate-limit responses.",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def run_pipeline(settings: Settings | None = None, email_to_override: str | None = None) -> dict[str, Any]:
    """Execute one end-to-end pipeline run."""
    _configure_logging()
    cfg = settings or get_settings()
    if email_to_override and email_to_override.strip():
        cfg = replace(cfg, email_to=email_to_override.strip())
    cfg.validate_pipeline_config()

    LOGGER.info("Pipeline started.")
    news = fetch_latest_news(cfg)
    filtered_news = filter_ai_news(news)
    if not filtered_news:
        raise ValueError("No AI-relevant news found after filtering.")

    csv_path = DATA_DIR / "news.csv"
    save_news_to_csv(filtered_news, csv_path)
    analytics = analyze_news(filtered_news)

    llm = GroqLLMService(cfg)
    used_llm_fallback = False
    llm_rate_limited = False
    try:
        summary_data = llm.summarize_news(filtered_news)
    except Exception as exc:
        if not _is_rate_limit_error(exc):
            raise
        LOGGER.warning("LLM summary rate-limited. Switching to deterministic fallback summary.")
        used_llm_fallback = True
        llm_rate_limited = True
        summary_data = _build_fallback_summary(filtered_news)

    if llm_rate_limited:
        LOGGER.warning("Skipping LLM blog generation because rate limit was already detected in this run.")
        used_llm_fallback = True
        blog_markdown = _build_fallback_blog(summary_data, filtered_news)
    else:
        try:
            blog_markdown = llm.generate_blog(summary_data, filtered_news)
        except Exception as exc:
            if not _is_rate_limit_error(exc):
                raise
            LOGGER.warning("LLM blog generation rate-limited. Switching to deterministic fallback blog.")
            used_llm_fallback = True
            blog_markdown = _build_fallback_blog(summary_data, filtered_news)

    blog_assets = build_blog_assets(blog_markdown, filtered_news)

    email_html = format_email_html(
        title=blog_assets["title"],
        summary_data=summary_data,
        blog_html=blog_assets["html"],
        analytics=analytics,
    )
    plain_text = blog_assets["markdown"]

    output_dir = Path("data")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "latest_blog.md").write_text(blog_assets["markdown"], encoding="utf-8")
    (output_dir / "latest_blog.html").write_text(email_html, encoding="utf-8")
    (output_dir / "latest_summary.json").write_text(json.dumps(summary_data, indent=2), encoding="utf-8")

    send_email(
        settings=cfg,
        subject=cfg.email_subject,
        html_body=email_html,
        plain_text_fallback=plain_text,
    )
    LOGGER.info("Pipeline finished successfully.")

    return {
        "status": "success",
        "articles": filtered_news,
        "analytics": {
            "article_count": analytics.get("article_count", 0),
            "top_keywords": analytics.get("top_keywords", []),
            "category_distribution": analytics.get("category_distribution", {}),
            "source_distribution": analytics.get("source_distribution", {}),
        },
        "summary": summary_data,
        "blog_title": blog_assets["title"],
        "used_llm_fallback": used_llm_fallback,
        "outputs": {
            "markdown_output": str((output_dir / "latest_blog.md").resolve()),
            "html_output": str((output_dir / "latest_blog.html").resolve()),
            "summary_output": str((output_dir / "latest_summary.json").resolve()),
        },
        "email_sent_to": cfg.email_to,
    }


if __name__ == "__main__":
    run_pipeline()
