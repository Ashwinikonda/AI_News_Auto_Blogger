"""Daily scheduler for the AI News Auto-Blogger pipeline."""

from __future__ import annotations

import logging
import time

import schedule

from config import get_settings
from main import run_pipeline

LOGGER = logging.getLogger(__name__)


def _run_job() -> None:
    try:
        run_pipeline()
    except Exception:
        LOGGER.exception("Scheduled pipeline run failed.")


def start_scheduler() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    settings = get_settings()
    settings.validate_pipeline_config()

    schedule.every().day.at(settings.schedule_time_24h).do(_run_job)
    LOGGER.info("Scheduler started. Daily run time: %s", settings.schedule_time_24h)

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    start_scheduler()
