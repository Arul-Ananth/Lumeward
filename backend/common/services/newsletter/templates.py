from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NewsletterTemplateDefinition:
    key: str
    name: str
    description: str
    cadence: str
    prompt_hint: str


BUILTIN_TEMPLATES: tuple[NewsletterTemplateDefinition, ...] = (
    NewsletterTemplateDefinition(
        key="daily_tech",
        name="Daily Tech Briefing",
        description="A compact technical digest grounded in current runtime date context.",
        cadence="daily",
        prompt_hint="Prioritize technical changes, developer tooling, AI, infrastructure, and security updates.",
    ),
    NewsletterTemplateDefinition(
        key="weekly_research",
        name="Weekly Research Digest",
        description="A deeper synthesis of local research themes and external developments.",
        cadence="weekly",
        prompt_hint="Connect recurring user research themes with recent papers, releases, and credible references.",
    ),
    NewsletterTemplateDefinition(
        key="morning_digest",
        name="Morning Digest",
        description="A concise morning briefing shaped by current interests and recent activity.",
        cadence="daily",
        prompt_hint="Keep it scan-friendly, practical, and ordered by what the user can act on today.",
    ),
    NewsletterTemplateDefinition(
        key="current_events",
        name="Current Events Summary",
        description="A date-grounded summary of current events with explicit uncertainty when search is unavailable.",
        cadence="on_demand",
        prompt_hint="Use runtime date context. Do not invent current events when web search cannot verify them.",
    ),
)


def get_template(template_key: str | None) -> NewsletterTemplateDefinition:
    key = template_key or "daily_tech"
    for template in BUILTIN_TEMPLATES:
        if template.key == key:
            return template
    return BUILTIN_TEMPLATES[0]
