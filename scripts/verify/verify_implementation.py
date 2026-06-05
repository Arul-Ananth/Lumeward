import asyncio

from _bootstrap import setup_project_path, use_temp_data_dir

setup_project_path()
tmp = use_temp_data_dir()

from backend.common.config import AppMode, settings
from backend.common.database import create_db_and_tables
from backend.common.services.memory import vector_db
from backend.common.services.newsletter.pipeline import newsletter_pipeline


async def main() -> None:
    settings.APP_MODE = AppMode.DESKTOP
    settings.configure()
    print(f"Forced Mode: {settings.APP_MODE}")
    print(f"Data Dir: {settings.DATA_DIR}")

    print("\n--- Starting Verification ---")
    print("Creating tables...")
    try:
        create_db_and_tables()
        print("Tables created successfully.")
    except Exception as exc:
        print(f"DB Error: {exc}")
        return

    print("Testing Newsletter Service (mocked)...")
    original_body = newsletter_pipeline._build_body
    newsletter_pipeline._build_body = lambda *args, **kwargs: "Mocked content for 'Python Async'"
    try:
        result = await newsletter_pipeline.generate_newsletter(topic="Python Async", user_id=1, persist=False)
        print(f"Success! Result: {result.content}")
    except Exception as exc:
        print(f"Service Error: {exc}")
        import traceback

        traceback.print_exc()
    finally:
        newsletter_pipeline._build_body = original_body
        vector_db.client.close()
        tmp.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
