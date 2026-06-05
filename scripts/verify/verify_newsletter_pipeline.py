import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

from _bootstrap import setup_project_path, use_temp_data_dir

setup_project_path()
tmp = use_temp_data_dir()

from sqlmodel import Session, select

from backend.common.config import AppMode, settings
from backend.common.database import create_db_and_tables, engine
from backend.common.models.sql import NewsletterDigest, NewsletterSchedule, User
from backend.common.security.policy import InputSanitizer
from backend.common.services.memory import vector_db
from backend.common.services.newsletter.pipeline import (
    archive_digest,
    due_schedules,
    list_digests,
    list_templates,
    newsletter_pipeline,
)
from backend.common.services.security_policy import authorize_network_action
from backend.desktop.workers.cron_digest import CronDigestWorker


async def main() -> int:
    settings.APP_MODE = AppMode.SERVER
    settings.ENGINE_ENABLED = True
    settings.ENGINE_BASE_URL = "https://trusted-engine.example/v1"
    settings.ENGINE_API_KEY = "test"
    settings.ENGINE_MODEL_NAME = "test-model"
    settings.configure()
    create_db_and_tables()

    original_body = newsletter_pipeline._build_body
    newsletter_pipeline._build_body = lambda *args, **kwargs: "### Mock Digest\n\n- Safe local insight."  # type: ignore[method-assign]
    try:
        with Session(engine) as session:
            user = User(email="verify@example.com", full_name="Verify User", hashed_password="disabled")
            session.add(user)
            session.commit()
            session.refresh(user)

            templates = list_templates(session)
            if not templates:
                print("FAIL: no newsletter templates registered.")
                return 1

            result = await newsletter_pipeline.generate_newsletter(
                topic="Python runtime news",
                user_id=user.id,
                session=session,
                template_key="daily_tech",
            )
            if "Mock Digest" not in result.content:
                print("FAIL: mocked pipeline result missing expected content.")
                return 1

            digests = list_digests(session, user.id)
            if len(digests) != 1:
                print(f"FAIL: expected one digest, got {len(digests)}")
                return 1

            archived = archive_digest(session, user.id, digests[0].id)
            if archived is None or not archived.archived:
                print("FAIL: digest archive did not persist.")
                return 1
            if list_digests(session, user.id):
                print("FAIL: archived digest is visible in default history.")
                return 1

            now = datetime.now(ZoneInfo("UTC"))
            schedule = NewsletterSchedule(
                user_id=user.id,
                name="Verify schedule",
                template_key="daily_tech",
                topic_seed="Python",
                cadence="daily",
                local_time=now.strftime("%H:%M"),
                timezone="UTC",
                enabled=True,
            )
            session.add(schedule)
            session.commit()
            due = due_schedules(session, now=now)
            if not due:
                print("FAIL: due schedule was not detected.")
                return 1

            generated = await asyncio.to_thread(lambda: CronDigestWorker(poll_seconds=999).run_once(now=now))
            if generated != 1:
                print(f"FAIL: cron worker generated {generated} digests, expected 1.")
                return 1
            persisted = session.exec(select(NewsletterDigest).where(NewsletterDigest.user_id == user.id)).all()
            if len(persisted) < 2:
                print("FAIL: cron generated digest was not persisted.")
                return 1

        allowed = authorize_network_action("engine.request", "https://trusted-engine.example/v1/chat/completions")
        denied = authorize_network_action("engine.request", "https://other-engine.example/v1/chat/completions")
        if not allowed.allowed or denied.allowed:
            print("FAIL: remote engine allowlist policy did not behave as expected.")
            return 1

        sanitized = InputSanitizer().sanitize_context("GEMINI_API_KEY=AIzaSySecretSecretSecretSecret")
        if "AIzaSySecret" in sanitized or "[REDACTED]" not in sanitized:
            print("FAIL: sanitizer did not redact API key.")
            return 1

        print("PASS: newsletter pipeline persistence, schedules, cron, policy, and sanitizer verified.")
        return 0
    finally:
        newsletter_pipeline._build_body = original_body  # type: ignore[method-assign]
        vector_db.client.close()
        tmp.cleanup()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
