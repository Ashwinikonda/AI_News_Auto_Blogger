"""Convert LLM output into publish-ready blog artifacts."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import markdown2


def _ensure_title(markdown_text: str) -> tuple[str, str]:
    lines = [line for line in markdown_text.splitlines() if line.strip()]
    if lines and lines[0].startswith("# "):
        title = lines[0][2:].strip()
        return title, markdown_text

    default_title = f"Daily AI News Brief - {datetime.utcnow().strftime('%Y-%m-%d')}"
    enriched = f"# {default_title}\n\n{markdown_text.strip()}"
    return default_title, enriched


def _inject_reference_links(markdown_text: str, news_items: list[dict[str, Any]]) -> str:
    references = []
    for idx, item in enumerate(news_items[:8], start=1):
        title = item.get("title", "Source")
        link = item.get("link", "")
        if not link:
            continue
        references.append(f"{idx}. [{title}]({link})")

    if not references:
        return markdown_text
    return markdown_text.strip() + "\n\n## Sources\n" + "\n".join(references) + "\n"


def build_blog_assets(blog_markdown: str, news_items: list[dict[str, Any]]) -> dict[str, str]:
    """Return Markdown and HTML blog outputs."""
    title, titled_markdown = _ensure_title(blog_markdown)
    final_markdown = _inject_reference_links(titled_markdown, news_items)
    final_markdown = re.sub(r"\n{3,}", "\n\n", final_markdown).strip() + "\n"

    html_body = markdown2.markdown(final_markdown, extras=["tables", "fenced-code-blocks", "strike"])
    return {
        "title": title,
        "markdown": final_markdown,
        "html": html_body,
    }
