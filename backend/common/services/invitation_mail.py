from __future__ import annotations

import smtplib
from dataclasses import dataclass
from email.message import EmailMessage

from backend.common.config import settings


@dataclass(frozen=True)
class MailDeliveryResult:
    status: str
    error: str | None = None


def invitation_url(raw_token: str) -> str:
    return f"{settings.FRONTEND_PUBLIC_URL.rstrip('/')}/invite/{raw_token}"


def send_invitation_email(*, recipient: str, organization_name: str, raw_token: str) -> MailDeliveryResult:
    """Send an invitation when SMTP is configured; the stored invitation remains usable on failure."""
    if not settings.SMTP_HOST.strip() or not settings.SMTP_FROM_EMAIL.strip():
        return MailDeliveryResult(status="not_configured")

    message = EmailMessage()
    message["Subject"] = f"You are invited to {organization_name} on Lumeward"
    message["From"] = settings.SMTP_FROM_EMAIL.strip()
    message["To"] = recipient
    link = invitation_url(raw_token)
    message.set_content(
        f"You have been invited to join {organization_name} on Lumeward.\n\n"
        f"Accept the invitation: {link}\n\n"
        f"This link expires in {settings.INVITATION_EXPIRE_DAYS} days."
    )

    smtp_type = smtplib.SMTP_SSL if settings.SMTP_USE_SSL else smtplib.SMTP
    try:
        with smtp_type(
            settings.SMTP_HOST.strip(),
            settings.SMTP_PORT,
            timeout=settings.SMTP_TIMEOUT_SECONDS,
        ) as client:
            if settings.SMTP_USE_TLS and not settings.SMTP_USE_SSL:
                client.starttls()
            if settings.SMTP_USERNAME:
                client.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            client.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        return MailDeliveryResult(status="failed", error=str(exc)[:500])
    return MailDeliveryResult(status="sent")
