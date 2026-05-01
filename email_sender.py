"""SMTP email delivery for generated AI blog."""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import Settings

LOGGER = logging.getLogger(__name__)


def send_email(settings: Settings, subject: str, html_body: str, plain_text_fallback: str) -> None:
    """Send email using SMTP STARTTLS."""
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = settings.email_from
    message["To"] = settings.email_to

    message.attach(MIMEText(plain_text_fallback, "plain", "utf-8"))
    message.attach(MIMEText(html_body, "html", "utf-8"))

    LOGGER.info("Sending email to %s via %s:%s", settings.email_to, settings.smtp_host, settings.smtp_port)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=settings.request_timeout_seconds) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(settings.smtp_username, settings.smtp_password)
        server.sendmail(settings.email_from, [settings.email_to], message.as_string())
    LOGGER.info("Email sent successfully.")
