"""Streamlit UI for AI News Auto-Blogger pipeline."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from config import get_settings
from main import run_pipeline


def _render_top_keywords(top_keywords: list) -> None:
    if not top_keywords:
        st.info("No keyword data available.")
        return

    keywords_df = pd.DataFrame(top_keywords, columns=["keyword", "count"])
    st.subheader("Top Keywords")
    st.dataframe(keywords_df, use_container_width=True)


def _render_category_distribution(category_distribution: dict) -> None:
    if not category_distribution:
        st.info("No category distribution available.")
        return

    category_df = pd.DataFrame(
        [{"category": k, "count": v} for k, v in category_distribution.items()]
    ).sort_values("count", ascending=False)
    st.subheader("Category Distribution")
    st.dataframe(category_df, use_container_width=True)
    st.bar_chart(category_df.set_index("category")["count"])


def main() -> None:
    st.set_page_config(page_title="AI News Auto Blogger Dashboard", layout="wide")
    st.title("AI News Auto Blogger Dashboard")
    st.caption("Run the complete pipeline on demand: fetch -> filter -> summarize -> blog -> email.")

    default_email = ""
    try:
        default_email = get_settings().email_to
    except Exception:
        pass

    email_to_input = st.text_input("Recipient Email (optional override)", value=default_email)
    run_clicked = st.button("Run Pipeline", type="primary")

    if not run_clicked:
        return

    with st.spinner("Running pipeline..."):
        try:
            result = run_pipeline(email_to_override=email_to_input or None)
        except Exception as exc:
            st.error(f"Pipeline failed: {exc}")
            st.exception(exc)
            return

    analytics = result.get("analytics", {})
    articles = result.get("articles", [])
    st.success(f"Pipeline completed. Email sent to: {result.get('email_sent_to', 'N/A')}")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total AI Articles", analytics.get("article_count", 0))
    with col2:
        st.metric("News Rows Displayed", len(articles))

    _render_top_keywords(analytics.get("top_keywords", []))
    _render_category_distribution(analytics.get("category_distribution", {}))

    st.subheader("Filtered News Articles")
    if articles:
        st.dataframe(pd.DataFrame(articles), use_container_width=True)
    else:
        st.info("No filtered articles available.")

    summary = result.get("summary", {})
    if summary:
        st.subheader("Executive Summary")
        st.write(summary.get("executive_summary", "Summary unavailable."))


if __name__ == "__main__":
    main()
