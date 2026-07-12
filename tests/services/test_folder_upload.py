from __future__ import annotations

import io
import zipfile

from sqlmodel import Session, select

from backend.common.database import get_engine
from backend.common.models.sql import EventRaw, FilesIndex, User
from backend.common.services.ingestion import folder_upload
from backend.common.services.ingestion.folder_upload import cleanup_managed_uploads_on_startup, ingest_folder_zip


def test_ingest_folder_zip_indexes_text_files_without_network(monkeypatch, isolated_data_dir, fake_embedder, fake_qdrant) -> None:
    client = fake_qdrant
    monkeypatch.setattr(folder_upload, "ensure_collection", lambda _: None)
    monkeypatch.setattr(folder_upload, "get_embedder", lambda: fake_embedder)
    monkeypatch.setattr(folder_upload, "client", client)

    archive_path = isolated_data_dir / "folder.zip"
    archive_path.write_bytes(_zip_bytes({"notes/readme.md": "# Local AI\nUseful local-first context."}))

    with Session(get_engine()) as session:
        user = User(email="upload@example.com", full_name="Upload User", hashed_password="disabled")
        session.add(user)
        session.commit()
        session.refresh(user)

        result = ingest_folder_zip(session, archive_path=archive_path, filename="folder.zip", user_id=user.id)

        assert result.status == "ok"
        assert result.files_seen == 1
        assert result.files_ingested == 1
        assert result.files_skipped == 0
        assert result.files_failed == 0
        assert client.points
        assert session.exec(select(FilesIndex)).one().status == "ingested"
        assert session.exec(select(EventRaw).where(EventRaw.event_type == "file_ingestion")).one()


def test_ingest_folder_zip_rejects_unsafe_paths(monkeypatch, isolated_data_dir, fake_embedder, fake_qdrant) -> None:
    monkeypatch.setattr(folder_upload, "ensure_collection", lambda _: None)
    monkeypatch.setattr(folder_upload, "get_embedder", lambda: fake_embedder)
    monkeypatch.setattr(folder_upload, "client", fake_qdrant)
    archive_path = isolated_data_dir / "bad.zip"
    archive_path.write_bytes(_zip_bytes({"../escape.md": "bad"}))

    with Session(get_engine()) as session:
        user = User(email="unsafe@example.com", full_name="Unsafe User", hashed_password="disabled")
        session.add(user)
        session.commit()
        session.refresh(user)

        try:
            ingest_folder_zip(session, archive_path=archive_path, filename="bad.zip", user_id=user.id)
        except ValueError as exc:
            assert "Unsafe archive path" in str(exc)
        else:
            raise AssertionError("unsafe archive path was accepted")


def test_cleanup_managed_uploads_preserves_indexed_metadata(monkeypatch, isolated_data_dir, fake_embedder, fake_qdrant) -> None:
    client = fake_qdrant
    monkeypatch.setattr(folder_upload, "ensure_collection", lambda _: None)
    monkeypatch.setattr(folder_upload, "get_embedder", lambda: fake_embedder)
    monkeypatch.setattr(folder_upload, "client", client)
    archive_path = isolated_data_dir / "folder.zip"
    archive_path.write_bytes(_zip_bytes({"notes/readme.md": "Cleanup should not delete metadata."}))

    with Session(get_engine()) as session:
        user = User(email="cleanup@example.com", full_name="Cleanup User", hashed_password="disabled")
        session.add(user)
        session.commit()
        session.refresh(user)
        ingest_folder_zip(session, archive_path=archive_path, filename="folder.zip", user_id=user.id)

    assert cleanup_managed_uploads_on_startup() == 1
    with Session(get_engine()) as session:
        assert session.exec(select(FilesIndex)).all()
        assert session.exec(select(EventRaw)).all()


def _zip_bytes(files: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path, content in files.items():
            archive.writestr(path, content)
    return buffer.getvalue()
