from __future__ import annotations

from datetime import datetime
from unittest.mock import Mock
from zoneinfo import ZoneInfo

from sqlmodel import Session

from backend.common.database import get_engine
from backend.common.models.sql import NewsletterSchedule, User
from backend.common.services.newsletter.pipeline import (
    archive_digest,
    due_schedules,
    list_digests,
    list_templates,
    newsletter_pipeline,
)
from backend.common.config import settings


async def test_newsletter_generation_persists_and_archives_digest(monkeypatch, isolated_data_dir) -> None:
    monkeypatch.setattr(
        newsletter_pipeline,
        "_build_body",
        lambda *args, **kwargs: "### Mock Digest\n\n- Safe local insight.",
    )

    with Session(get_engine()) as session:
        user = User(email="newsletter@example.com", full_name="Newsletter User", hashed_password="disabled")
        session.add(user)
        session.commit()
        session.refresh(user)

        assert list_templates(session)
        result = await newsletter_pipeline.generate_newsletter(
            topic="Python runtime news",
            user_id=user.id,
            session=session,
            template_key="daily_tech",
        )

        assert "Mock Digest" in result.content
        digests = list_digests(session, user.id)
        assert len(digests) == 1

        archived = archive_digest(session, user.id, digests[0].id)
        assert archived is not None
        assert archived.archived is True
        assert list_digests(session, user.id) == []


def test_due_schedules_returns_enabled_matching_local_time(isolated_data_dir) -> None:
    now = datetime.now(ZoneInfo("UTC"))
    with Session(get_engine()) as session:
        user = User(email="schedule@example.com", full_name="Schedule User", hashed_password="disabled")
        session.add(user)
        session.commit()
        session.refresh(user)
        schedule = NewsletterSchedule(
            user_id=user.id,
            name="Daily schedule",
            template_key="daily_tech",
            topic_seed="Python",
            cadence="daily",
            local_time=now.strftime("%H:%M"),
            timezone="UTC",
            enabled=True,
        )
        session.add(schedule)
        session.commit()

        assert due_schedules(session, now=now) == [schedule]


def test_ollama_uses_one_search_then_direct_generation(monkeypatch, isolated_data_dir) -> None:
    from backend.common.services.newsletter import pipeline as pipeline_module
    from backend.common.services.llm import crew_builder

    llm = Mock()
    direct = Mock(return_value="Direct local briefing")
    search_tool = Mock()
    search_tool.run.return_value = "Three bounded search results"
    monkeypatch.setattr(settings, "LLM_PROVIDER", "ollama")
    monkeypatch.setattr(pipeline_module, "build_search_tools", lambda **_kwargs: [search_tool])
    monkeypatch.setattr(pipeline_module, "get_memory_context", lambda **_kwargs: "")
    monkeypatch.setattr(pipeline_module, "get_recent_clipboard_context", lambda **_kwargs: "")
    monkeypatch.setattr(pipeline_module, "build_llm", lambda **_kwargs: llm)
    monkeypatch.setattr(crewai_builder := crew_builder, "generate_newsletter_direct", direct)

    body = newsletter_pipeline._build_body(
        "tech hiring",
        1,
        "context",
        {},
        None,
        pipeline_module.get_template(None),
        datetime.now(ZoneInfo("UTC")),
    )

    assert body == "Direct local briefing"
    direct.assert_called_once()
    search_tool.run.assert_called_once_with(query="tech hiring")
    assert "Three bounded search results" in direct.call_args.kwargs["context"]
