from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NewsletterSourceCapability:
    key: str
    display_name: str
    status: str
    supported_platforms: list[str]
    required_permissions: list[str]
    implemented: bool = False


PLANNED_SOURCE_CAPABILITIES = (
    NewsletterSourceCapability(
        key="telegram",
        display_name="Telegram",
        status="planned_beta_placeholder",
        supported_platforms=["windows", "macos", "linux", "server"],
        required_permissions=["network:https://api.telegram.org", "secret:telegram_bot_token"],
    ),
    NewsletterSourceCapability(
        key="whatsapp_export",
        display_name="WhatsApp Export",
        status="planned_beta_placeholder",
        supported_platforms=["windows", "macos", "linux"],
        required_permissions=["file:user_selected_export", "storage:local_source_items"],
    ),
    NewsletterSourceCapability(
        key="rss",
        display_name="RSS / Atom",
        status="planned_beta_placeholder",
        supported_platforms=["windows", "macos", "linux", "server"],
        required_permissions=["network:feed_url"],
    ),
    NewsletterSourceCapability(
        key="email",
        display_name="Email",
        status="planned_beta_placeholder",
        supported_platforms=["windows", "macos", "linux", "server"],
        required_permissions=["network:imap_or_provider_api", "secret:email_access_token"],
    ),
)


def list_source_capabilities() -> list[NewsletterSourceCapability]:
    return list(PLANNED_SOURCE_CAPABILITIES)
