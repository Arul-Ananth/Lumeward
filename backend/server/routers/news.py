import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from backend.common.config import settings
from backend.common.database import get_session
from backend.common.models.sql import NewsletterSchedule, NewsletterTemplate
from backend.common.models.schemas import (
    FeedbackRequest,
    FeedbackResponse,
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
from backend.common.services.auth.resolver import get_current_principal
from backend.common.services.auth.types import AuthPrincipal
from backend.common.services.memory import vector_db
from backend.common.services.newsletter.pipeline import (
    archive_digest,
    get_digest,
    list_digests,
    list_schedules,
    list_templates,
    newsletter_pipeline,
    sync_builtin_templates,
)
from backend.common.services.newsletter.sources import list_source_capabilities
from backend.server.services import billing

logger = logging.getLogger(__name__)

router = APIRouter(tags=["News"])


@router.post("/generate", response_model=NewsResponse)
async def generate_news(
    request: NewsRequest,
    principal: AuthPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_session),
):
    billing.check_funds(session, principal.user_id)

    context = vector_db.get_user_context(principal.user_id, request.topic)

    try:
        api_keys = {
            "serper_api_key": request.serper_api_key,
            "openai_api_key": request.openai_api_key,
        }
        result_response = await newsletter_pipeline.generate_newsletter(
            topic=request.topic,
            user_id=principal.user_id,
            session=session,
            context=str(context),
            api_keys=api_keys,
            template_key=request.template_key,
        )
        content = result_response.content
        input_tok = 100
        output_tok = 100
    except Exception as exc:
        logger.exception("Newsletter generation failed: %s", exc)
        raise HTTPException(status_code=500, detail="Newsletter generation failed.") from exc

    receipt = billing.process_transaction(session, principal.user_id, request.topic, input_tok, output_tok)

    return NewsResponse(
        topic=request.topic,
        content=content,
        bill=receipt,
    )


@router.get("/templates", response_model=list[NewsletterTemplateResponse])
def get_templates(session: Session = Depends(get_session)):
    return [
        NewsletterTemplateResponse(
            key=template.key,
            name=template.name,
            description=template.description,
            cadence=template.cadence,
            prompt_hint=template.prompt_hint,
        )
        for template in list_templates(session)
    ]


@router.get("/sources", response_model=list[NewsletterSourceCapabilityResponse])
def get_sources():
    return [
        NewsletterSourceCapabilityResponse(
            key=source.key,
            display_name=source.display_name,
            status=source.status,
            supported_platforms=source.supported_platforms,
            required_permissions=source.required_permissions,
            implemented=source.implemented,
        )
        for source in list_source_capabilities()
    ]


@router.get("/history", response_model=list[NewsletterDigestResponse])
def get_history(
    include_archived: bool = False,
    principal: AuthPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_session),
):
    return [_digest_response(digest) for digest in list_digests(session, principal.user_id, include_archived=include_archived)]


@router.get("/history/{digest_id}", response_model=NewsletterDigestResponse)
def read_digest(
    digest_id: int,
    principal: AuthPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_session),
):
    digest = get_digest(session, principal.user_id, digest_id)
    if digest is None:
        raise HTTPException(status_code=404, detail="Digest not found")
    return _digest_response(digest)


@router.post("/history/{digest_id}/archive", response_model=NewsletterDigestResponse)
def archive_history_digest(
    digest_id: int,
    principal: AuthPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_session),
):
    digest = archive_digest(session, principal.user_id, digest_id)
    if digest is None:
        raise HTTPException(status_code=404, detail="Digest not found")
    return _digest_response(digest)


@router.get("/schedules", response_model=list[NewsletterScheduleResponse])
def get_schedules(
    principal: AuthPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_session),
):
    return [_schedule_response(schedule) for schedule in list_schedules(session, principal.user_id)]


@router.post("/schedules", status_code=201, response_model=NewsletterScheduleResponse)
def create_schedule(
    request: NewsletterScheduleCreate,
    principal: AuthPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_session),
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
    return _schedule_response(schedule)


@router.patch("/schedules/{schedule_id}", response_model=NewsletterScheduleResponse)
def update_schedule(
    schedule_id: int,
    request: NewsletterScheduleUpdate,
    principal: AuthPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_session),
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
    return _schedule_response(schedule)


@router.delete("/schedules/{schedule_id}", response_model=MessageResponse)
def delete_schedule(
    schedule_id: int,
    principal: AuthPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_session),
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
    principal: AuthPrincipal = Depends(get_current_principal),
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
    principal: AuthPrincipal = Depends(get_current_principal),
):
    memories = vector_db.fetch_memories(principal.user_id)
    return ProfileResponse(memories=memories)


@router.get("/profile/{user_id}", response_model=ProfileResponse)
def get_profile(
    user_id: int,
    principal: AuthPrincipal = Depends(get_current_principal),
):
    if not settings.is_trusted_lan_auth() and user_id != principal.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this profile")

    effective_user_id = principal.user_id if settings.is_trusted_lan_auth() else user_id
    memories = vector_db.fetch_memories(effective_user_id)
    return ProfileResponse(memories=memories)


def _digest_response(digest) -> NewsletterDigestResponse:
    return NewsletterDigestResponse(
        id=digest.id,
        template_key=digest.template_key,
        title=digest.title,
        topic=digest.topic,
        markdown=digest.markdown,
        html=digest.html,
        archived=digest.archived,
        created_at=digest.created_at.isoformat(),
    )


def _schedule_response(schedule: NewsletterSchedule) -> NewsletterScheduleResponse:
    return NewsletterScheduleResponse(
        id=schedule.id,
        name=schedule.name,
        template_key=schedule.template_key,
        topic_seed=schedule.topic_seed,
        cadence=schedule.cadence,
        local_time=schedule.local_time,
        timezone=schedule.timezone,
        enabled=schedule.enabled,
        last_run_at=schedule.last_run_at.isoformat() if schedule.last_run_at else None,
        created_at=schedule.created_at.isoformat(),
        updated_at=schedule.updated_at.isoformat(),
    )


def _get_user_schedule(session: Session, user_id: int, schedule_id: int) -> NewsletterSchedule | None:
    schedule = session.get(NewsletterSchedule, schedule_id)
    if schedule is None or schedule.user_id != user_id:
        return None
    return schedule
