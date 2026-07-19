from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from dataclasses import dataclass
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlmodel import Session, select

from backend.common.config import settings
from backend.common.models.schemas import NewsResponse
from backend.common.models.sql import NewsletterDigest, NewsletterSchedule, NewsletterTemplate
from backend.common.services.llm.provider_factory import build_llm
from backend.common.services.llm.tool_policy import build_search_tools
from backend.common.services.memory.memory_sanitizer import sanitize_memory_context
from backend.common.services.memory.vector_db import (
    get_memory_context,
    get_recent_clipboard_context,
    is_clipboard_history_query,
)
from backend.common.services.newsletter.compiler import compile_html, compile_markdown, title_for_digest
from backend.common.services.newsletter.templates import BUILTIN_TEMPLATES, NewsletterTemplateDefinition, get_template

TIME_SENSITIVE_TERMS = (
    "today",
    "todays",
    "current date",
    "actual current date",
    "latest",
    "recent",
)
CURRENT_EVENTS_TERMS = (
    "world events",
    "world event",
    "world news",
    "news today",
    "current events",
    "headlines",
)


@dataclass(frozen=True)
class GenerationRequest:
    """Canonical input shared by interactive, feed, and scheduled generation."""

    user_id: int
    topic: str
    source: str = "interactive"
    template_key: str | None = None
    context: str = ""
    api_keys: dict | None = None
    session_id: str | None = None
    source_schedule_id: int | None = None
    persist: bool = True
    workspace_ids: tuple[int, ...] = ()
    organization_ids: tuple[int, ...] = ()


def sync_builtin_templates(session: Session) -> None:
    for template in BUILTIN_TEMPLATES:
        existing = session.get(NewsletterTemplate, template.key)
        if existing is None:
            existing = NewsletterTemplate(
                key=template.key,
                name=template.name,
                description=template.description,
                cadence=template.cadence,
                prompt_hint=template.prompt_hint,
                is_builtin=True,
            )
        else:
            existing.name = template.name
            existing.description = template.description
            existing.cadence = template.cadence
            existing.prompt_hint = template.prompt_hint
            existing.updated_at = datetime.utcnow()
        session.add(existing)
    session.commit()


def list_templates(session: Session) -> list[NewsletterTemplate]:
    sync_builtin_templates(session)
    return list(session.exec(select(NewsletterTemplate).order_by(NewsletterTemplate.name)).all())


def list_digests(session: Session, user_id: int, *, include_archived: bool = False) -> list[NewsletterDigest]:
    statement = select(NewsletterDigest).where(NewsletterDigest.user_id == user_id)
    if not include_archived:
        statement = statement.where(NewsletterDigest.archived == False)  # noqa: E712
    return list(session.exec(statement.order_by(NewsletterDigest.created_at.desc())).all())


def get_digest(session: Session, user_id: int, digest_id: int) -> NewsletterDigest | None:
    digest = session.get(NewsletterDigest, digest_id)
    if digest is None or digest.user_id != user_id:
        return None
    return digest


def archive_digest(session: Session, user_id: int, digest_id: int) -> NewsletterDigest | None:
    digest = get_digest(session, user_id, digest_id)
    if digest is None:
        return None
    digest.archived = True
    session.add(digest)
    session.commit()
    session.refresh(digest)
    return digest


def list_schedules(session: Session, user_id: int) -> list[NewsletterSchedule]:
    return list(
        session.exec(
            select(NewsletterSchedule)
            .where(NewsletterSchedule.user_id == user_id)
            .order_by(NewsletterSchedule.created_at.desc())
        ).all()
    )


def due_schedules(session: Session, now: datetime | None = None) -> list[NewsletterSchedule]:
    current = now or datetime.now().astimezone()
    schedules = session.exec(select(NewsletterSchedule).where(NewsletterSchedule.enabled == True)).all()  # noqa: E712
    return [schedule for schedule in schedules if _schedule_due(schedule, current)]


def _schedule_due(schedule: NewsletterSchedule, now: datetime) -> bool:
    try:
        local_now = now.astimezone(ZoneInfo(schedule.timezone))
    except ZoneInfoNotFoundError:
        local_now = now
    if local_now.strftime("%H:%M") != schedule.local_time:
        return False
    if schedule.last_run_at is None:
        return True
    elapsed = datetime.utcnow() - schedule.last_run_at
    if schedule.cadence == "weekly":
        return elapsed >= timedelta(days=6, hours=23)
    return elapsed >= timedelta(hours=23)


def mark_schedule_run(session: Session, schedule: NewsletterSchedule) -> None:
    schedule.last_run_at = datetime.utcnow()
    schedule.updated_at = datetime.utcnow()
    session.add(schedule)
    session.commit()


class NewsletterPipeline:
    async def generate(self, request: GenerationRequest, *, session: Session | None = None) -> NewsResponse:
        return await self.generate_newsletter(
            topic=request.topic,
            user_id=request.user_id,
            session=session,
            context=request.context,
            api_keys=request.api_keys,
            session_id=request.session_id,
            template_key=request.template_key,
            source_schedule_id=request.source_schedule_id,
            persist=request.persist,
            workspace_ids=request.workspace_ids,
            organization_ids=request.organization_ids,
        )

    async def generate_newsletter(
        self,
        *,
        topic: str,
        user_id: int,
        session: Session | None = None,
        context: str = "",
        api_keys: dict | None = None,
        session_id: str | None = None,
        template_key: str | None = None,
        source_schedule_id: int | None = None,
        persist: bool = True,
        workspace_ids: tuple[int, ...] = (),
        organization_ids: tuple[int, ...] = (),
    ) -> NewsResponse:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            self._run_generation,
            topic,
            user_id,
            context,
            api_keys or {},
            session_id,
            template_key,
            workspace_ids,
            organization_ids,
        )
        markdown = result["markdown"]
        if session is not None and persist:
            sync_builtin_templates(session)
            digest = NewsletterDigest(
                user_id=user_id,
                template_key=result["template"].key,
                title=result["title"],
                topic=topic,
                markdown=markdown,
                html=result["html"],
                source_schedule_id=source_schedule_id,
            )
            session.add(digest)
            session.commit()
        return NewsResponse(topic=topic, content=markdown)

    def _run_generation(
        self,
        topic: str,
        user_id: int,
        context: str,
        api_keys: dict,
        session_id: str | None,
        template_key: str | None,
        workspace_ids: tuple[int, ...],
        organization_ids: tuple[int, ...],
    ) -> dict:
        now = datetime.now().astimezone()
        template = get_template(template_key)
        body = self._build_body(topic, user_id, context, api_keys, session_id, template, now, workspace_ids, organization_ids)
        title = title_for_digest(template=template, topic=topic, now=now)
        markdown = compile_markdown(title=title, topic=topic, template=template, body=body, runtime_date=now)
        return {
            "template": template,
            "title": title,
            "markdown": markdown,
            "html": compile_html(markdown),
        }

    def _build_body(
        self,
        topic: str,
        user_id: int,
        context: str,
        api_keys: dict,
        session_id: str | None,
        template: NewsletterTemplateDefinition,
        now: datetime,
        workspace_ids: tuple[int, ...] = (),
        organization_ids: tuple[int, ...] = (),
    ) -> str:
        clipboard_query = is_clipboard_history_query(topic)
        time_sensitive = _is_time_sensitive_query(topic)
        current_events_query = _is_current_events_query(topic) or template.key == "current_events"
        date_only_query = _needs_current_date(topic) and not current_events_query and not clipboard_query
        tools = [] if clipboard_query else build_search_tools(api_keys=api_keys)

        memory_context = get_memory_context(
            user_id=user_id,
            topic=topic,
            session_id=session_id,
            workspace_ids=workspace_ids,
            organization_ids=organization_ids,
        )
        clipboard_context = get_recent_clipboard_context(topic=topic, session_id=session_id)
        safe_memory = sanitize_memory_context(memory_context) if memory_context else ""
        combined_context = self._combined_context(
            base=context,
            template=template,
            safe_memory=safe_memory,
            clipboard_context=clipboard_context,
            clipboard_query=clipboard_query,
            now=now,
            time_sensitive=time_sensitive or current_events_query,
        )
        if clipboard_query and _clipboard_missing(clipboard_context):
            return (
                "### Clipboard History\n\n"
                "No relevant clipboard history was found for this request. "
                "The app did not find a recent clipboard entry matching your query."
            )
        if date_only_query:
            return _format_date_only_response(now)
        if current_events_query:
            return self._build_current_events_brief(now=now, tools=tools)

        llm = build_llm(api_keys=api_keys)
        from backend.common.services.llm.crew_builder import (
            build_newsletter_crew,
            generate_newsletter_direct,
        )

        provider = (settings.LLM_PROVIDER or "ollama").strip().lower()
        if provider == "ollama":
            direct_context = combined_context
            if tools:
                try:
                    search_result = str(tools[0].run(query=topic)).strip()
                except Exception as exc:
                    search_result = f"Search unavailable: {exc}"
                if search_result:
                    direct_context = f"{direct_context}\n\nExternal Research:\n{search_result}"
            return generate_newsletter_direct(
                topic=topic,
                context=direct_context,
                llm=llm,
                time_sensitive=time_sensitive,
                runtime_date_label=_runtime_date_label(now) if time_sensitive else None,
            )

        crew = build_newsletter_crew(
            topic=topic,
            context=combined_context,
            llm=llm,
            tools=tools,
            time_sensitive=time_sensitive,
            runtime_date_label=_runtime_date_label(now) if time_sensitive else None,
        )
        return str(crew.kickoff())

    def _combined_context(
        self,
        *,
        base: str,
        template: NewsletterTemplateDefinition,
        safe_memory: str,
        clipboard_context: str,
        clipboard_query: bool,
        now: datetime,
        time_sensitive: bool,
    ) -> str:
        sections = [base.strip(), f"Newsletter Template Guidance:\n{template.prompt_hint}"]
        if clipboard_context:
            sections.append(clipboard_context)
        if safe_memory:
            sections.append(f"Memory Context:\n{safe_memory}")
        if clipboard_query:
            sections.append(
                "Instruction: This is a clipboard-history question. Answer from Clipboard History Context first. "
                "Do not use external research for this request."
            )
        if time_sensitive:
            sections.append(_runtime_datetime_context(now))
        return "\n\n".join(section for section in sections if section).strip()

    def _build_current_events_brief(self, *, now: datetime, tools: list) -> str:
        date_label = _runtime_date_label(now)
        if not tools:
            return (
                "### Global News Update\n\n"
                f"**Date:** {date_label}\n\n"
                "Current-date web search is unavailable, so Lumeward cannot verify today's world events right now."
            )
        result = tools[0].run(f"world news {date_label}")
        if _search_unavailable(result):
            return (
                "### Global News Update\n\n"
                f"**Date:** {date_label}\n\n"
                "Lumeward could not verify today's world events from web search right now."
            )
        lines = _clean_search_lines(result)
        if not lines:
            return (
                "### Global News Update\n\n"
                f"**Date:** {date_label}\n\n"
                "Lumeward did not receive enough current-event search results to summarize today reliably."
            )
        return (
            "### Global News Update\n\n"
            f"**Date:** {date_label}\n\n"
            "Based on current web-search results:\n"
            + "\n".join(f"- {line}" for line in lines)
        )


def _is_time_sensitive_query(topic: str) -> bool:
    lowered = topic.lower()
    return any(term in lowered for term in TIME_SENSITIVE_TERMS)


def _is_current_events_query(topic: str) -> bool:
    lowered = topic.lower()
    return _is_time_sensitive_query(topic) and any(term in lowered for term in CURRENT_EVENTS_TERMS)


def _needs_current_date(topic: str) -> bool:
    lowered = topic.lower()
    return "today" in lowered or "todays date" in lowered or "today's date" in lowered or "current date" in lowered


def _runtime_date_label(now: datetime) -> str:
    return now.strftime("%B %d, %Y")


def _runtime_datetime_context(now: datetime) -> str:
    return (
        "Runtime Date Context:\n"
        f"- Today is {_runtime_date_label(now)}.\n"
        f"- Local timestamp: {now.isoformat()}.\n"
        "- Treat references to 'today' and 'current' as this local runtime date."
    )


def _format_date_only_response(now: datetime) -> str:
    return (
        "### Current Date\n\n"
        f"Today is **{_runtime_date_label(now)}**.\n\n"
        f"Local timestamp: `{now.isoformat()}`"
    )


def _clean_search_lines(result: str, *, limit: int = 3) -> list[str]:
    lines: list[str] = []
    for raw in result.splitlines():
        cleaned = raw.strip()
        if not cleaned:
            continue
        if cleaned.startswith("-"):
            cleaned = cleaned[1:].strip()
        if cleaned:
            lines.append(cleaned)
        if len(lines) >= limit:
            break
    return lines


def _search_unavailable(result: str) -> bool:
    lowered = result.lower()
    markers = (
        "web search unavailable",
        "fallback search unavailable",
        "error executing",
        "no results",
        "no extractable content",
        "search blocked by security policy",
    )
    return any(marker in lowered for marker in markers)


def _clipboard_missing(clipboard_context: str) -> bool:
    return (
        "No recent clipboard entries were captured." in clipboard_context
        or "No recent clipboard entries matched:" in clipboard_context
    )


newsletter_pipeline = NewsletterPipeline()
