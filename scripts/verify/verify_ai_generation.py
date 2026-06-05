import asyncio

from _bootstrap import setup_project_path, use_temp_data_dir

setup_project_path()
tmp = use_temp_data_dir()

from backend.common.config import AppMode, settings
from backend.common.services.memory import vector_db
from backend.common.services.newsletter.pipeline import newsletter_pipeline


async def _run_for_mode(mode: AppMode) -> bool:
    settings.APP_MODE = mode
    settings.configure()

    original_body = newsletter_pipeline._build_body
    newsletter_pipeline._build_body = lambda *args, **kwargs: f"Mocked content for Testing ({mode.value})"
    try:
        result = await newsletter_pipeline.generate_newsletter(
            topic="Testing",
            user_id=1,
            context="context",
            api_keys={},
            session_id="verify",
            persist=False,
        )
    finally:
        newsletter_pipeline._build_body = original_body

    if not result.content or mode.value not in result.content:
        print(f"FAIL: unexpected content for {mode.value}: {result.content}")
        return False
    return True


async def main() -> int:
    try:
        ok_desktop = await _run_for_mode(AppMode.DESKTOP)
        ok_server = await _run_for_mode(AppMode.SERVER)
        return 0 if (ok_desktop and ok_server) else 1
    finally:
        vector_db.client.close()
        tmp.cleanup()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
