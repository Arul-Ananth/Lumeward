import asyncio
import logging
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from sqlmodel import Session

from backend.common.config import settings
from backend.common.database import get_session, session_scope
from backend.common.models.sql import NewsletterSchedule, NewsletterTemplate
from backend.common.models.schemas import (
    FeedbackRequest,
    FeedbackResponse,
    FeedCardResponse,
    FolderIngestResponse,
    MessageResponse,
    NewsRequest,
    NewsResponse,
    NewsletterDigestResponse,
    NewsletterScheduleCreate,
    NewsletterScheduleResponse,
    NewsletterScheduleUpdate,
    NewsletterSourceCapabilityResponse,
    NewsletterTemplateResponse,
    ProfileResponse,
)
from backend.common.services.intelligence_feed.feed_deep_dive import run_deep_dive
from backend.common.services.intelligence_feed.feed_router import IntelligenceFeedRouter
from backend.common.services.ingestion import ingest_folder_zip
from backend.common.services.ingestion.folder_upload import upload_root
from backend.common.services.auth.resolver import get_current_principal
from backend.common.services.auth.types import AuthPrincipal
from backend.common.services.memory import vector_db
from backend.common.services.memory.vector_db import QdrantUnavailableError
from backend.common.services.newsletter.pipeline import (
    GenerationRequest,
    archive_digest,
    get_digest,
    list_digests,
    list_schedules,
    list_templates,
    newsletter_pipeline,
    sync_builtin_templates,
)
from backend.common.services.newsletter.sources import list_source_capabilities

logger = logging.getLogger(__name__)

router = APIRouter(tags=["News"])
feed_router = IntelligenceFeedRouter()
ingestion_semaphore = asyncio.Semaphore(max(1, settings.INGESTION_CONCURRENCY))
UPLOAD_CHUNK_BYTES = 1024 * 1024
CurrentPrincipal = Annotated[AuthPrincipal, Depends(get_current_principal)]
DbSession = Annotated[Session, Depends(get_session)]


@router.post("/generate", response_model=NewsResponse)
async def generate_news(
    request: NewsRequest,
    principal: CurrentPrincipal,
    session: DbSession,
):
    context = await asyncio.to_thread(vector_db.get_user_context, principal.user_id, request.topic)

    try:
        result_response = await newsletter_pipeline.generate(
            GenerationRequest(
                topic=request.topic,
                user_id=principal.user_id,
                source="web",
                context=str(context),
                template_key=request.template_key,
            ),
            session=session,
        )
        content = result_response.content
    except QdrantUnavailableError:
        raise
    except Exception as exc:
        logger.exception("Newsletter generation failed: %s", exc)
        raise HTTPException(status_code=500, detail="Newsletter generation failed.") from exc

    return NewsResponse(
        topic=request.topic,
        content=content,
    )


@router.get("/templates", response_model=list[NewsletterTemplateResponse])
def get_templates(session: DbSession):
    return list_templates(session)


@router.get("/sources", response_model=list[NewsletterSourceCapabilityResponse])
def get_sources():
    return list_source_capabilities()


@router.get("/feed", response_model=list[FeedCardResponse])
def get_feed(
    principal: CurrentPrincipal,
    session: DbSession,
):
    feed_router.process_new_events(session, principal.user_id)
    return feed_router.list_cards(session, principal.user_id)


@router.post("/feed/{feed_id}/dismiss", response_model=FeedCardResponse)
def dismiss_feed_card(
    feed_id: int,
    principal: CurrentPrincipal,
    session: DbSession,
):
    card = feed_router.dismiss(session, principal.user_id, feed_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Feed card not found")
    return card


@router.post("/feed/{feed_id}/deep-dive", response_model=NewsResponse)
async def deep_dive_feed_card(
    feed_id: int,
    principal: CurrentPrincipal,
    session: DbSession,
):
    try:
        content = await run_deep_dive(session, user_id=principal.user_id, feed_id=feed_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except QdrantUnavailableError:
        raise
    except Exception as exc:
        logger.exception("Feed deep dive failed: %s", exc)
        raise HTTPException(status_code=500, detail="Feed deep dive failed.") from exc
    return NewsResponse(topic=f"Feed card {feed_id}", content=content)


@router.post("/ingest/folder", response_model=FolderIngestResponse)
async def ingest_folder_upload(
    request: Request,
    file: UploadFile,
    principal: CurrentPrincipal,
):
    try:
        result = await _run_bounded_ingestion(
            file,
            file.filename or "folder.zip",
            principal.user_id,
            request.headers.get("content-length"),
        )
    except UploadTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Folder upload ingestion failed: %s", exc)
        raise HTTPException(status_code=500, detail="Folder upload ingestion failed.") from exc
    return result


class UploadTooLargeError(ValueError):
    """Raised when an upload exceeds the configured compressed-size limit."""


def _stream_upload_to_temp(file: UploadFile) -> Path:
    max_bytes = settings.FOLDER_UPLOAD_MAX_ARCHIVE_MB * 1024 * 1024
    total = 0
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            suffix=".zip",
            prefix="incoming-",
            dir=upload_root(),
            delete=False,
        ) as destination:
            temporary_path = Path(destination.name)
            while chunk := file.file.read(UPLOAD_CHUNK_BYTES):
                total += len(chunk)
                if total > max_bytes:
                    raise UploadTooLargeError(
                        f"Archive exceeds {settings.FOLDER_UPLOAD_MAX_ARCHIVE_MB} MB."
                    )
                destination.write(chunk)
        return temporary_path
    except Exception:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise


def _ingest_folder_in_worker(archive_path: Path, filename: str, user_id: int):
    with session_scope() as session:
        return ingest_folder_zip(
            session,
            archive_path=archive_path,
            filename=filename,
            user_id=user_id,
            session_id="server-upload",
        )


async def _run_bounded_ingestion(
    file: UploadFile,
    filename: str,
    user_id: int,
    content_length: str | None = None,
):
    max_bytes = settings.FOLDER_UPLOAD_MAX_ARCHIVE_MB * 1024 * 1024
    if file.size is not None and file.size > max_bytes:
        raise UploadTooLargeError(f"Archive exceeds {settings.FOLDER_UPLOAD_MAX_ARCHIVE_MB} MB.")
    if content_length is not None:
        try:
            request_bytes = int(content_length)
        except ValueError:
            request_bytes = 0
        if request_bytes > max_bytes + UPLOAD_CHUNK_BYTES:
            raise UploadTooLargeError(f"Archive exceeds {settings.FOLDER_UPLOAD_MAX_ARCHIVE_MB} MB.")

    async with ingestion_semaphore:
        archive_path = await asyncio.to_thread(_stream_upload_to_temp, file)
        try:
            return await asyncio.to_thread(_ingest_folder_in_worker, archive_path, filename, user_id)
        finally:
            archive_path.unlink(missing_ok=True)


@router.get("/history", response_model=list[NewsletterDigestResponse])
def get_history(
    principal: CurrentPrincipal,
    session: DbSession,
    include_archived: bool = False,
):
    return list_digests(session, principal.user_id, include_archived=include_archived)


@router.get("/history/{digest_id}", response_model=NewsletterDigestResponse)
def read_digest(
    digest_id: int,
    principal: CurrentPrincipal,
    session: DbSession,
):
    digest = get_digest(session, principal.user_id, digest_id)
    if digest is None:
        raise HTTPException(status_code=404, detail="Digest not found")
    return digest


@router.post("/history/{digest_id}/archive", response_model=NewsletterDigestResponse)
def archive_history_digest(
    digest_id: int,
    principal: CurrentPrincipal,
    session: DbSession,
):
    digest = archive_digest(session, principal.user_id, digest_id)
    if digest is None:
        raise HTTPException(status_code=404, detail="Digest not found")
    return digest


@router.get("/schedules", response_model=list[NewsletterScheduleResponse])
def get_schedules(
    principal: CurrentPrincipal,
    session: DbSession,
):
    return list_schedules(session, principal.user_id)


@router.post("/schedules", status_code=201, response_model=NewsletterScheduleResponse)
def create_schedule(
    request: NewsletterScheduleCreate,
    principal: CurrentPrincipal,
    session: DbSession,
):
    sync_builtin_templates(session)
    if session.get(NewsletterTemplate, request.template_key) is None:
        raise HTTPException(status_code=400, detail="Unknown newsletter template")
    schedule = NewsletterSchedule(
        user_id=principal.user_id,
        name=request.name,
        template_key=request.template_key,
        topic_seed=request.topic_seed,
        cadence=request.cadence,
        local_time=request.local_time,
        timezone=request.timezone,
        enabled=request.enabled,
    )
    session.add(schedule)
    session.commit()
    session.refresh(schedule)
    return schedule


@router.patch("/schedules/{schedule_id}", response_model=NewsletterScheduleResponse)
def update_schedule(
    schedule_id: int,
    request: NewsletterScheduleUpdate,
    principal: CurrentPrincipal,
    session: DbSession,
):
    schedule = _get_user_schedule(session, principal.user_id, schedule_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    updates = request.model_dump(exclude_unset=True)
    if "template_key" in updates:
        sync_builtin_templates(session)
        if session.get(NewsletterTemplate, updates["template_key"]) is None:
            raise HTTPException(status_code=400, detail="Unknown newsletter template")
    for field, value in updates.items():
        setattr(schedule, field, value)
    schedule.updated_at = datetime.utcnow()
    session.add(schedule)
    session.commit()
    session.refresh(schedule)
    return schedule


@router.delete("/schedules/{schedule_id}", response_model=MessageResponse)
def delete_schedule(
    schedule_id: int,
    principal: CurrentPrincipal,
    session: DbSession,
):
    schedule = _get_user_schedule(session, principal.user_id, schedule_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    session.delete(schedule)
    session.commit()
    return MessageResponse(message="Schedule deleted")


@router.post("/feedback", response_model=FeedbackResponse)
def submit_feedback(
    feedback: FeedbackRequest,
    principal: CurrentPrincipal,
):
    vector_db.save_feedback(
        principal.user_id,
        feedback.original_topic,
        feedback.feedback_text,
        feedback.sentiment,
    )
    return FeedbackResponse(status="Feedback recorded")


@router.get("/profile", response_model=ProfileResponse)
def get_current_profile(
    principal: CurrentPrincipal,
):
    memories = vector_db.fetch_memories(principal.user_id)
    return ProfileResponse(memories=memories)


@router.get("/profile/{user_id}", response_model=ProfileResponse)
def get_profile(
    user_id: int,
    principal: CurrentPrincipal,
):
    if not settings.is_trusted_lan_auth() and user_id != principal.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this profile")

    effective_user_id = principal.user_id if settings.is_trusted_lan_auth() else user_id
    memories = vector_db.fetch_memories(effective_user_id)
    return ProfileResponse(memories=memories)


def _get_user_schedule(session: Session, user_id: int, schedule_id: int) -> NewsletterSchedule | None:
    schedule = session.get(NewsletterSchedule, schedule_id)
    if schedule is None or schedule.user_id != user_id:
        return None
    return schedule
