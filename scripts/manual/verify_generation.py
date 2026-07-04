import asyncio
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
if str(root) not in sys.path:
    sys.path.append(str(root))

from backend.common.config import AppMode, settings
from backend.common.services.newsletter.pipeline import newsletter_pipeline


async def main() -> None:
    settings.APP_MODE = AppMode.DESKTOP
    settings.configure()

    print("--- Starting Real Generation Test ---")
    print(f"Provider: {settings.LLM_PROVIDER}")
    print(f"URL: {settings.OPENAI_API_BASE}")
    print(f"Model: {settings.OPENAI_MODEL_NAME}")

    try:
        print("Sending request to LLM (this may take time)...")
        result = await newsletter_pipeline.generate_newsletter(topic="Physics", user_id=1)
        print("\n--- Result Content ---")
        print(result.content[:500] + "...")
        print("--- End Result ---")
    except Exception as exc:
        print(f"ERROR: {exc}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
