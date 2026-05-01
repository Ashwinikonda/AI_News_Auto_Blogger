"""GROQ LLM integration for summary and blog generation."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

import requests

from config import PROMPTS_DIR, Settings

LOGGER = logging.getLogger(__name__)

SUMMARIZATION_PROMPT_KEY = "[NEWS_SUMMARIZATION_PROMPT]"
BLOG_PROMPT_KEY = "[BLOG_GENERATION_PROMPT]"
MAX_RETRIES = 2
MAX_BACKOFF_SECONDS = 10


def _read_prompts_file(prompts_path: Path) -> tuple[str, str]:
    raw_text = prompts_path.read_text(encoding="utf-8")
    if SUMMARIZATION_PROMPT_KEY not in raw_text or BLOG_PROMPT_KEY not in raw_text:
        raise ValueError("prompts.txt must include [NEWS_SUMMARIZATION_PROMPT] and [BLOG_GENERATION_PROMPT] sections.")

    summary_section = raw_text.split(SUMMARIZATION_PROMPT_KEY, maxsplit=1)[1].split(BLOG_PROMPT_KEY, maxsplit=1)[0].strip()
    blog_section = raw_text.split(BLOG_PROMPT_KEY, maxsplit=1)[1].strip()
    return summary_section, blog_section


class GroqLLMService:
    """Client wrapper for GROQ OpenAI-compatible chat completions API."""

    def __init__(self, settings: Settings, prompts_path: Path | None = None) -> None:
        self.settings = settings
        self.prompts_path = prompts_path or (PROMPTS_DIR / "prompts.txt")
        self.summary_prompt, self.blog_prompt = _read_prompts_file(self.prompts_path)

    def _chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 1600,
    ) -> str:
        url = f"{self.settings.groq_base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.settings.groq_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.settings.groq_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        response = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = requests.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=self.settings.request_timeout_seconds,
                )
                if response.status_code == 429:
                    wait_seconds = self._resolve_retry_wait(response, attempt)
                    if attempt >= MAX_RETRIES:
                        break
                    LOGGER.warning(
                        "GROQ API rate limited (attempt %s/%s). Retrying in %s seconds.",
                        attempt,
                        MAX_RETRIES,
                        wait_seconds,
                    )
                    time.sleep(wait_seconds)
                    continue
                response.raise_for_status()
                break
            except requests.Timeout:
                if attempt >= MAX_RETRIES:
                    raise
                wait_seconds = min(2 ** (attempt - 1), MAX_BACKOFF_SECONDS)
                LOGGER.warning(
                    "GROQ API timeout (attempt %s/%s). Retrying in %s seconds.",
                    attempt,
                    MAX_RETRIES,
                    wait_seconds,
                )
                time.sleep(wait_seconds)
            except requests.RequestException:
                raise

        if response is None:
            raise RuntimeError("Unable to complete GROQ request due to repeated transient failures.")
        if response.status_code == 429:
            raise RuntimeError(
                "Groq API rate limit reached. Please wait 1-2 minutes and try again, "
                "or upgrade your Groq plan limits."
            )

        data = response.json()
        choices = data.get("choices", [])
        if not choices:
            raise ValueError("No choices returned from GROQ API.")
        content = choices[0].get("message", {}).get("content", "").strip()
        if not content:
            raise ValueError("Empty content returned from GROQ API.")
        return content

    @staticmethod
    def _resolve_retry_wait(response: requests.Response, attempt: int) -> int:
        retry_after = response.headers.get("Retry-After", "").strip()
        if retry_after.isdigit():
            return max(1, min(int(retry_after), MAX_BACKOFF_SECONDS))
        return min(2 ** (attempt - 1), MAX_BACKOFF_SECONDS)

    @staticmethod
    def _compact_news_payload(news_items: list[dict[str, Any]], limit: int = 8) -> list[dict[str, str]]:
        compact = []
        for item in news_items[:limit]:
            compact.append(
                {
                    "title": str(item.get("title", "")),
                    "source": str(item.get("source", "")),
                    "published_at": str(item.get("published_at", "")),
                    "snippet": str(item.get("snippet", "")),
                    "link": str(item.get("link", "")),
                    "category": str(item.get("category", "")),
                }
            )
        return compact

    def summarize_news(self, filtered_news: list[dict[str, Any]]) -> dict[str, Any]:
        payload = self._compact_news_payload(filtered_news)
        user_prompt = (
            "News dataset JSON:\n"
            f"{json.dumps(payload, ensure_ascii=False, indent=2)}\n\n"
            "Return only valid JSON matching the requested schema."
        )
        raw_output = self._chat_completion(
            system_prompt=self.summary_prompt,
            user_prompt=user_prompt,
            temperature=0.1,
            max_tokens=700,
        )
        try:
            return json.loads(raw_output)
        except json.JSONDecodeError:
            LOGGER.warning("LLM summary output was not valid JSON. Wrapping as fallback text.")
            return {"executive_summary": raw_output, "key_points": [], "top_stories": []}

    def generate_blog(self, summary_data: dict[str, Any], filtered_news: list[dict[str, Any]]) -> str:
        payload = {
            "summary_data": summary_data,
            "news_items": self._compact_news_payload(filtered_news),
        }
        user_prompt = (
            "Use this structured input and generate the final SEO-friendly blog article in Markdown:\n"
            f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
        )
        return self._chat_completion(
            system_prompt=self.blog_prompt,
            user_prompt=user_prompt,
            temperature=0.35,
            max_tokens=1200,
        )
