"""Central configuration for the AI News Auto-Blogger pipeline."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
TEMPLATES_DIR = BASE_DIR / "templates"
PROMPTS_DIR = BASE_DIR / "prompts"


def _get_from_streamlit_secrets(key: str) -> str:
    """Best-effort secret lookup for Streamlit Cloud deployments."""
    try:
        import streamlit as st  # Lazy import to keep CLI usage simple.

        value = st.secrets.get(key, "")
        return str(value).strip() if value is not None else ""
    except Exception:
        return ""


def _env_or_secret(*keys: str, default: str = "") -> str:
    """Read value from env first, then Streamlit secrets."""
    for key in keys:
        env_value = os.getenv(key, "").strip()
        if env_value:
            return env_value
        secret_value = _get_from_streamlit_secrets(key)
        if secret_value:
            return secret_value
    return default


@dataclass(frozen=True)
class Settings:
    """Runtime settings loaded from environment variables."""

    serpapi_key: str
    groq_api_key: str
    groq_model: str
    groq_base_url: str
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    email_from: str
    email_to: str
    email_subject: str
    news_query: str
    news_results_limit: int
    news_country: str
    news_language: str
    schedule_time_24h: str
    request_timeout_seconds: int

    @classmethod
    def from_env(cls) -> "Settings":
        serpapi_key = _env_or_secret("SERPAPI_API_KEY", "SERPAPI_KEY")
        smtp_username = _env_or_secret("SMTP_USERNAME", "EMAIL_USER")
        smtp_password = _env_or_secret("SMTP_PASSWORD", "EMAIL_PASS")

        return cls(
            serpapi_key=serpapi_key,
            groq_api_key=_env_or_secret("GROQ_API_KEY"),
            groq_model=_env_or_secret("GROQ_MODEL", default="llama-3.3-70b-versatile"),
            groq_base_url=_env_or_secret("GROQ_BASE_URL", default="https://api.groq.com/openai/v1"),
            smtp_host=_env_or_secret("SMTP_HOST", default="smtp.gmail.com"),
            smtp_port=int(_env_or_secret("SMTP_PORT", default="587")),
            smtp_username=smtp_username,
            smtp_password=smtp_password,
            email_from=_env_or_secret("EMAIL_FROM"),
            email_to=_env_or_secret("EMAIL_TO"),
            email_subject=_env_or_secret("EMAIL_SUBJECT", default="Daily AI News Brief"),
            news_query=_env_or_secret(
                "NEWS_QUERY",
                default="artificial intelligence OR generative AI OR large language model OR machine learning",
            ),
            news_results_limit=int(_env_or_secret("NEWS_RESULTS_LIMIT", default="20")),
            news_country=_env_or_secret("NEWS_COUNTRY", default="us"),
            news_language=_env_or_secret("NEWS_LANGUAGE", default="en"),
            schedule_time_24h=_env_or_secret("SCHEDULE_TIME_24H", default="09:00"),
            request_timeout_seconds=int(_env_or_secret("REQUEST_TIMEOUT_SECONDS", default="30")),
        )

    def validate_pipeline_config(self) -> None:
        required = {
            "SERPAPI_API_KEY": self.serpapi_key,
            "GROQ_API_KEY": self.groq_api_key,
            "SMTP_USERNAME": self.smtp_username,
            "SMTP_PASSWORD": self.smtp_password,
            "EMAIL_FROM": self.email_from,
            "EMAIL_TO": self.email_to,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            joined = ", ".join(missing)
            raise ValueError(f"Missing required environment variables: {joined}")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""
    settings = Settings.from_env()
    return settings
