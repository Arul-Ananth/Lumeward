"""Compatibility wrapper for older imports.

Active newsletter orchestration lives in ``backend.common.services.newsletter``.
Keep this module so existing desktop workers, scripts, and external callers can
continue importing ``newsletter_service`` during the migration.
"""

from __future__ import annotations

from sqlmodel import Session

from backend.common.models.schemas import NewsResponse
from backend.common.services.newsletter.pipeline import newsletter_pipeline


class NewsletterService:
    async def generate_newsletter(
        self,
        topic: str,
        user_id: int,
        context: str = "",
        api_keys: dict | None = None,
        session_id: str | None = None,
        *,
        session: Session | None = None,
        template_key: str | None = None,
        persist: bool = True,
    ) -> NewsResponse:
        return await newsletter_pipeline.generate_newsletter(
            topic=topic,
            user_id=user_id,
            session=session,
            context=context,
            api_keys=api_keys or {},
            session_id=session_id,
            template_key=template_key,
            persist=persist,
        )


newsletter_service = NewsletterService()
