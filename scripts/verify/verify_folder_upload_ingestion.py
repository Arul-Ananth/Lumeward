from __future__ import annotations

import io
import os
import warnings
import zipfile

from _bootstrap import setup_project_path, use_temp_data_dir

setup_project_path()
tmp = use_temp_data_dir()
warnings.filterwarnings(
    "ignore",
    message="Using `httpx` with `starlette.testclient` is deprecated.*",
    category=Warning,
)

from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import Session, select  # noqa: E402

from backend.common.config import AppMode, settings  # noqa: E402
from backend.common.database import create_db_and_tables, get_engine  # noqa: E402
from backend.common.models.sql import EventRaw, FilesIndex, IntelligenceFeed  # noqa: E402
from backend.common.services.ingestion import cleanup_managed_uploads_on_startup  # noqa: E402
from backend.common.services.intelligence_feed.feed_router import IntelligenceFeedRouter  # noqa: E402
from backend.common.services.memory import vector_db  # noqa: E402
from backend.server.app import create_app  # noqa: E402


def main() -> int:
    try:
        # Exercise the server route with isolated local storage; production server
        # storage requirements are covered by verify_storage_modes.py.
        settings.APP_MODE = AppMode.DESKTOP
        settings.TRUSTED_LAN_MODE = True
        settings.AUTH_MODE = None
        settings.FOLDER_UPLOAD_ENABLED = True
        settings.FOLDER_UPLOAD_DELETE_ON_RESTART = False
        settings.FOLDER_UPLOAD_MAX_ARCHIVE_MB = 1
        settings.FOLDER_UPLOAD_MAX_EXPANDED_MB = 1
        settings.FOLDER_UPLOAD_MAX_FILES = 10
        create_db_and_tables()

        app = create_app()
        with TestClient(app) as client:
            valid_zip = _zip_bytes(
                {
                    "notes/readme.md": "# Local AI\nUseful local-first context for Lumeward.",
                    "notes/skip.exe": "not allowed",
                }
            )
            response = client.post(
                "/news/ingest/folder",
                files={"file": ("folder.zip", valid_zip, "application/zip")},
            )
            if response.status_code != 200:
                print(f"FAIL: upload returned {response.status_code}: {response.text}")
                return 1
            payload = response.json()
            if payload["files_seen"] != 1 or payload["files_ingested"] != 1 or payload["files_skipped"] != 0:
                print(f"FAIL: unexpected ingest counts: {payload}")
                return 1

            upload_root = settings.DATA_DIR / settings.FOLDER_UPLOAD_DIR
            if not (upload_root / payload["batch_id"]).exists():
                print("FAIL: upload staging was deleted before restart cleanup.")
                return 1

            with Session(get_engine()) as session:
                files = session.exec(select(FilesIndex)).all()
                events = session.exec(select(EventRaw).where(EventRaw.event_type == "file_ingestion")).all()
                if not files or not events:
                    print("FAIL: FilesIndex or EventRaw file_ingestion row was not created.")
                    return 1
                created = IntelligenceFeedRouter().process_new_events(session, 1)
                cards = session.exec(select(IntelligenceFeed)).all()
                if created < 1 or not cards:
                    print("FAIL: Personal Feed card was not created from file ingestion event.")
                    return 1

            bad_zip = _zip_bytes({"../escape.md": "bad"})
            bad_response = client.post(
                "/news/ingest/folder",
                files={"file": ("bad.zip", bad_zip, "application/zip")},
            )
            if bad_response.status_code != 400:
                print(f"FAIL: unsafe zip path returned {bad_response.status_code}, expected 400")
                return 1

            oversized_response = client.post(
                "/news/ingest/folder",
                files={"file": ("large.zip", b"x" * (1024 * 1024 + 1), "application/zip")},
            )
            if oversized_response.status_code != 413:
                print(
                    f"FAIL: oversized upload returned {oversized_response.status_code}, expected 413"
                )
                return 1

            expanded_zip = _zip_bytes({"large.md": "a" * (1024 * 1024 + 1)})
            expanded_response = client.post(
                "/news/ingest/folder",
                files={"file": ("expanded.zip", expanded_zip, "application/zip")},
            )
            if expanded_response.status_code != 400:
                print(
                    f"FAIL: expanded-size violation returned {expanded_response.status_code}, expected 400"
                )
                return 1

        settings.FOLDER_UPLOAD_DELETE_ON_RESTART = False
        preserved = cleanup_managed_uploads_on_startup()
        if preserved != 0 or not any(upload_root.iterdir()):
            print("FAIL: cleanup disabled did not preserve staging files.")
            return 1

        settings.FOLDER_UPLOAD_DELETE_ON_RESTART = True
        removed = cleanup_managed_uploads_on_startup()
        if removed < 1 or any(upload_root.iterdir()):
            print("FAIL: cleanup enabled did not remove managed upload staging.")
            return 1

        with Session(get_engine()) as session:
            if not session.exec(select(FilesIndex)).all() or not session.exec(select(IntelligenceFeed)).all():
                print("FAIL: cleanup removed indexed metadata.")
                return 1

        print("PASS: folder upload ingestion and restart cleanup verified.")
        return 0
    finally:
        vector_db.client.close()
        tmp.cleanup()


def _zip_bytes(files: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path, content in files.items():
            archive.writestr(path, content)
    return buffer.getvalue()


if __name__ == "__main__":
    raise SystemExit(main())
