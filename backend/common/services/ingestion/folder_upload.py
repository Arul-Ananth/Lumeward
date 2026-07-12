from __future__ import annotations

import shutil
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from sqlmodel import Session

from backend.common.config import settings
from backend.common.services.memory.vector_db import client, ensure_collection, get_embedder
from backend.common.services.ingestion.document_service import document_ingestion

ALLOWED_EXTENSIONS = {".txt", ".md", ".html", ".pdf", ".docx"}


@dataclass(frozen=True)
class FolderIngestResult:
    status: str
    batch_id: str
    files_seen: int
    files_ingested: int
    files_skipped: int
    files_failed: int
    message: str


def cleanup_managed_uploads_on_startup() -> int:
    if not settings.FOLDER_UPLOAD_DELETE_ON_RESTART:
        return 0
    root = upload_root()
    if not root.exists():
        return 0
    removed = 0
    for child in root.iterdir():
        _assert_inside(child, root)
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
        removed += 1
    return removed


def upload_root() -> Path:
    relative = Path(settings.FOLDER_UPLOAD_DIR)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("FOLDER_UPLOAD_DIR must be a relative path inside DATA_DIR.")
    root = settings.DATA_DIR / relative
    root.mkdir(parents=True, exist_ok=True)
    _assert_inside(root, settings.DATA_DIR)
    return root


def ingest_folder_zip(
    session: Session,
    *,
    archive_path: Path,
    filename: str,
    user_id: int,
    session_id: str = "server-upload",
) -> FolderIngestResult:
    if not settings.FOLDER_UPLOAD_ENABLED:
        raise ValueError("Folder upload ingestion is disabled.")
    if not filename.lower().endswith(".zip"):
        raise ValueError("Folder upload requires a .zip archive.")

    max_archive_bytes = settings.FOLDER_UPLOAD_MAX_ARCHIVE_MB * 1024 * 1024
    if archive_path.stat().st_size > max_archive_bytes:
        raise ValueError(f"Archive exceeds {settings.FOLDER_UPLOAD_MAX_ARCHIVE_MB} MB.")

    batch_id = uuid.uuid4().hex
    batch_dir = upload_root() / batch_id
    extract_dir = batch_dir / "extracted"
    batch_dir.mkdir(parents=True, exist_ok=False)
    extract_dir.mkdir(parents=True, exist_ok=True)
    _assert_inside(batch_dir, upload_root())

    staged_archive_path = batch_dir / _safe_archive_name(filename)
    shutil.move(str(archive_path), staged_archive_path)

    try:
        with zipfile.ZipFile(staged_archive_path) as archive:
            members = [member for member in archive.infolist() if not member.is_dir()]
            if len(members) > settings.FOLDER_UPLOAD_MAX_FILES:
                raise ValueError(f"Archive contains more than {settings.FOLDER_UPLOAD_MAX_FILES} files.")
            expanded_bytes = sum(member.file_size for member in members)
            max_expanded_bytes = settings.FOLDER_UPLOAD_MAX_EXPANDED_MB * 1024 * 1024
            if expanded_bytes > max_expanded_bytes:
                raise ValueError(
                    f"Archive expands beyond {settings.FOLDER_UPLOAD_MAX_EXPANDED_MB} MB."
                )
            extracted_paths = _extract_members(archive, members, extract_dir)
    except zipfile.BadZipFile as exc:
        shutil.rmtree(batch_dir, ignore_errors=True)
        raise ValueError("Uploaded file is not a valid ZIP archive.") from exc
    except ValueError:
        shutil.rmtree(batch_dir, ignore_errors=True)
        raise

    seen = len(extracted_paths)
    ingested = 0
    skipped = 0
    failed = 0
    for path in extracted_paths:
        outcome = _ingest_file(session, path=path, user_id=user_id, session_id=session_id, batch_id=batch_id)
        if outcome == "ingested":
            ingested += 1
        elif outcome == "failed":
            failed += 1
        else:
            skipped += 1

    status = "ok" if failed == 0 else "partial"
    return FolderIngestResult(
        status=status,
        batch_id=batch_id,
        files_seen=seen,
        files_ingested=ingested,
        files_skipped=skipped,
        files_failed=failed,
        message=f"Folder archive processed. {ingested} files ingested.",
    )


def _extract_members(archive: zipfile.ZipFile, members: list[zipfile.ZipInfo], extract_dir: Path) -> list[Path]:
    extracted: list[Path] = []
    for member in members:
        relative = _safe_member_path(member)
        if relative is None:
            continue
        target = extract_dir / Path(*relative.parts)
        _assert_inside(target, extract_dir)
        target.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(member) as source, target.open("wb") as destination:
            shutil.copyfileobj(source, destination)
        extracted.append(target)
    return extracted


def _safe_member_path(member: zipfile.ZipInfo) -> PurePosixPath | None:
    path = PurePosixPath(member.filename)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"Unsafe archive path: {member.filename}")
    if _is_zip_symlink(member):
        raise ValueError(f"Archive symlinks are not allowed: {member.filename}")
    if path.suffix.lower() not in ALLOWED_EXTENSIONS:
        return None
    if any(part.startswith(".") for part in path.parts):
        return None
    return path


def _is_zip_symlink(member: zipfile.ZipInfo) -> bool:
    mode = member.external_attr >> 16
    return (mode & 0o170000) == 0o120000


def _ingest_file(session: Session, *, path: Path, user_id: int, session_id: str, batch_id: str) -> str:
    return document_ingestion.ingest(
        session,
        path=path,
        user_id=user_id,
        session_id=session_id,
        batch_id=batch_id,
        source="folder_upload",
        visibility="private",
        ensure_collection_fn=ensure_collection,
        embedder_fn=get_embedder,
        qdrant_client=client,
    )


def _safe_archive_name(filename: str) -> str:
    name = Path(filename).name
    return name if name.lower().endswith(".zip") else "folder.zip"


def _assert_inside(path: Path, root: Path) -> None:
    resolved = path.resolve()
    resolved_root = root.resolve()
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise ValueError(f"Path escapes managed upload directory: {path}")
