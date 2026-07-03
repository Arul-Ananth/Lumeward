from pathlib import Path
import sys
import uuid

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from sqlmodel import Session, select

from backend.common.database import get_engine
from backend.common.models.sql import EventRaw
from backend.common.services.memory.vector_db import get_recent_clipboard_context
from backend.common.services.telemetry.event_bus import EventPriority, TelemetryEvent
from backend.common.services.telemetry.workers import _hash_payload


def main() -> int:
    session_id = f'verify-clipboard-{uuid.uuid4().hex}'
    payload = {
        'user_id': 1,
        'text': 'LangChain helps developers build LLM applications with chains, agents, and retrieval.',
        'url': '',
        'content_hash': uuid.uuid4().hex,
        'ts': '2026-03-21T00:00:00',
    }
    event = TelemetryEvent(
        event_type='clipboard',
        session_id=session_id,
        payload=payload,
        source='clipboard',
        priority=EventPriority.IMPORTANT,
        content_hash=payload['content_hash'],
    )
    raw = EventRaw(
        event_type=event.event_type,
        ts=event.ts,
        session_id=event.session_id,
        payload_json='{"user_id": 1, "text": "LangChain helps developers build LLM applications with chains, agents, and retrieval.", "url": "", "content_hash": "%s", "ts": "2026-03-21T00:00:00"}' % payload['content_hash'],
        hash=_hash_payload(event),
        source=event.source,
    )

    with Session(get_engine()) as session:
        session.add(raw)
        session.commit()

    try:
        context = get_recent_clipboard_context('tell me what i know about langchain from my clipboard history', session_id=session_id)
        print(context)
        if 'LangChain helps developers build LLM applications' not in context:
            print('FAIL: clipboard query did not resolve the recent matching clipboard text.')
            return 1
        print('PASS: clipboard query resolved recent clipboard text directly.')
        return 0
    finally:
        with Session(get_engine()) as session:
            rows = session.exec(select(EventRaw).where(EventRaw.session_id == session_id)).all()
            for row in rows:
                session.delete(row)
            session.commit()


if __name__ == '__main__':
    raise SystemExit(main())
