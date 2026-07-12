from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.common.config import AppMode, settings
from backend.common.database import create_db_and_tables, dispose_database
from backend.common.services.memory import vector_db


@pytest.fixture
def isolated_data_dir(tmp_path: Path) -> Iterator[Path]:
    original_values = {
        "APP_MODE": settings.APP_MODE,
        "AUTH_MODE": settings.AUTH_MODE,
        "TRUSTED_LAN_MODE": settings.TRUSTED_LAN_MODE,
        "DATA_DIR": settings.DATA_DIR,
        "DATABASE_URL": settings.DATABASE_URL,
        "QDRANT_URL": settings.QDRANT_URL,
        "FOLDER_UPLOAD_ENABLED": settings.FOLDER_UPLOAD_ENABLED,
        "FOLDER_UPLOAD_DELETE_ON_RESTART": settings.FOLDER_UPLOAD_DELETE_ON_RESTART,
        "FOLDER_UPLOAD_MAX_ARCHIVE_MB": settings.FOLDER_UPLOAD_MAX_ARCHIVE_MB,
        "FOLDER_UPLOAD_MAX_EXPANDED_MB": settings.FOLDER_UPLOAD_MAX_EXPANDED_MB,
        "FOLDER_UPLOAD_MAX_FILES": settings.FOLDER_UPLOAD_MAX_FILES,
        "DOC_MAX_MB": settings.DOC_MAX_MB,
        "CHUNK_SIZE": settings.CHUNK_SIZE,
        "CHUNK_OVERLAP": settings.CHUNK_OVERLAP,
    }
    dispose_database()
    vector_db.close_qdrant()
    settings.APP_MODE = AppMode.DESKTOP
    settings.AUTH_MODE = None
    settings.TRUSTED_LAN_MODE = True
    settings.DATA_DIR = tmp_path
    settings.DATABASE_URL = ""
    settings.QDRANT_URL = ""
    settings.FOLDER_UPLOAD_ENABLED = True
    settings.FOLDER_UPLOAD_DELETE_ON_RESTART = True
    settings.FOLDER_UPLOAD_MAX_ARCHIVE_MB = 1
    settings.FOLDER_UPLOAD_MAX_EXPANDED_MB = 1
    settings.FOLDER_UPLOAD_MAX_FILES = 10
    settings.DOC_MAX_MB = 1
    settings.CHUNK_SIZE = 200
    settings.CHUNK_OVERLAP = 20
    create_db_and_tables()
    try:
        yield tmp_path
    finally:
        dispose_database()
        vector_db.close_qdrant()
        for name, value in original_values.items():
            setattr(settings, name, value)
