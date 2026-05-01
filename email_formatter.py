"""Format blog data into an email-ready HTML payload."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from config import TEMPLATES_DIR


def _analytics_html(analytics: dict[str, Any]) -> str:
    top_keywords = analytics.get("top_keywords", [])
    sources = analytics.get("source_distribution", {})
    categories = analytics.get("category_distribution", {})

    keywords_block = "".join([f"<li><strong>{k}</strong>: {v}</li>" for k, v in top_keywords[:10]])
    source_block = "".join([f"<li><strong>{k}</strong>: {v}</li>" for k, v in sources.items()])
    category_block = "".join([f"<li><strong>{k}</strong>: {v}</li>" for k, v in categories.items()])

    return f"""
    <h3>Data Snapshot</h3>
    <p><strong>Number of AI articles:</strong> {analytics.get("article_count", 0)}</p>
    <h4>Top Keywords</h4>
    <ul>{keywords_block or "<li>No keyword data</li>"}</ul>
    <h4>Source Distribution</h4>
    <ul>{source_block or "<li>No source data</li>"}</ul>
    <h4>Category Distribution</h4>
    <ul>{category_block or "<li>No category data</li>"}</ul>
    """


def format_email_html(
    title: str,
    summary_data: dict[str, Any],
    blog_html: str,
    analytics: dict[str, Any],
    template_path: Path | None = None,
) -> str:
    template = (template_path or (TEMPLATES_DIR / "email_template.html")).read_text(encoding="utf-8")
    summary_text = summary_data.get("executive_summary", "Summary unavailable.")
    key_points = summary_data.get("key_points", [])
    key_points_html = "".join(f"<li>{point}</li>" for point in key_points)
    analytics_block = _analytics_html(analytics)

    return (
        template.replace("{{TITLE}}", title)
        .replace("{{DATE}}", datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))
        .replace("{{SUMMARY}}", summary_text)
        .replace("{{KEY_POINTS}}", key_points_html or "<li>No key points returned</li>")
        .replace("{{BLOG_CONTENT}}", blog_html)
        .replace("{{ANALYTICS}}", analytics_block)
    )
