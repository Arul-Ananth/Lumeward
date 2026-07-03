from __future__ import annotations

import logging
from pathlib import Path

from sqlmodel import select

from backend.common.database import session_scope
from backend.common.models.sql import FolderConsent

logger = logging.getLogger(__name__)


def get_consented_folders() -> list[Path]:
    with session_scope() as session:
        rows = session.exec(select(FolderConsent)).all()
    return [Path(row.path) for row in rows]


def add_folder_consent(path: Path) -> None:
    with session_scope() as session:
        existing = session.get(FolderConsent, str(path))
        if existing:
            return
        session.add(FolderConsent(path=str(path)))
        session.commit()
        logger.info("Stored folder consent: %s", path)


def has_folder_consent(path: Path) -> bool:
    with session_scope() as session:
        return session.get(FolderConsent, str(path)) is not None
