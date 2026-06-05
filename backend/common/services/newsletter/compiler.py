from __future__ import annotations

import html
import re
from datetime import datetime

from backend.common.services.newsletter.templates import NewsletterTemplateDefinition


def title_for_digest(*, template: NewsletterTemplateDefinition, topic: str, now: datetime) -> str:
    date_label = now.strftime("%B %d, %Y")
    clean_topic = topic.strip() or template.name
    return f"{template.name}: {clean_topic} ({date_label})"


def compile_markdown(
    *,
    title: str,
    topic: str,
    template: NewsletterTemplateDefinition,
    body: str,
    runtime_date: datetime,
) -> str:
    cleaned_body = body.strip() or "No newsletter content was generated."
    return (
        f"# {title}\n\n"
        f"**Template:** {template.name}\n\n"
        f"**Topic:** {topic.strip()}\n\n"
        f"**Runtime date:** {runtime_date.isoformat()}\n\n"
        f"{cleaned_body}"
    ).strip()


def compile_html(markdown: str) -> str:
    lines = markdown.splitlines()
    html_lines: list[str] = []
    in_list = False
    for raw in lines:
        line = raw.strip()
        if not line:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            continue
        if line.startswith("# "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<h1>{html.escape(line[2:].strip())}</h1>")
            continue
        if line.startswith("## "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<h2>{html.escape(line[3:].strip())}</h2>")
            continue
        if line.startswith("- "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{_format_inline(line[2:].strip())}</li>")
            continue
        if in_list:
            html_lines.append("</ul>")
            in_list = False
        html_lines.append(f"<p>{_format_inline(line)}</p>")
    if in_list:
        html_lines.append("</ul>")
    return "\n".join(html_lines)


def _format_inline(text: str) -> str:
    escaped = html.escape(text)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
