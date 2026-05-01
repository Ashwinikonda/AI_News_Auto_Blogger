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
    summary_data = llm.summarize_news(filtered_news)
    blog_markdown = llm.generate_blog(summary_data, filtered_news)
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
        "outputs": {
            "markdown_output": str((output_dir / "latest_blog.md").resolve()),
            "html_output": str((output_dir / "latest_blog.html").resolve()),
            "summary_output": str((output_dir / "latest_summary.json").resolve()),
        },
        "email_sent_to": cfg.email_to,
    }


if __name__ == "__main__":
    run_pipeline()
