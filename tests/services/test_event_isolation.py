from sqlmodel import Session

from backend.common.config import AppMode, settings
from backend.common.database import get_engine
from backend.common.models.sql import EventRaw, User
from backend.common.services.intelligence_feed.ingestion_events import load_unprocessed_events


def test_feed_event_loading_is_owner_scoped(isolated_data_dir) -> None:
    with Session(get_engine()) as session:
        first = User(email="first@example.com", full_name="First", hashed_password="disabled")
        second = User(email="second@example.com", full_name="Second", hashed_password="disabled")
        session.add(first)
        session.add(second)
        session.commit()
        session.refresh(first)
        session.refresh(second)

        session.add_all(
            [
                EventRaw(
                    event_type="clipboard",
                    session_id="first-session",
                    payload_json='{"text":"First user private engineering context."}',
                    hash="first-event",
                    source="clipboard",
                    owner_user_id=first.id,
                    visibility="private",
                ),
                EventRaw(
                    event_type="clipboard",
                    session_id="second-session",
                    payload_json='{"text":"Second user private finance context."}',
                    hash="second-event",
                    source="clipboard",
                    owner_user_id=second.id,
                    visibility="private",
                ),
            ]
        )
        session.commit()

        events = load_unprocessed_events(session, int(first.id))

    assert len(events) == 1
    assert events[0].content_hash == "first-event"


def test_server_feed_does_not_consume_unowned_legacy_events(isolated_data_dir) -> None:
    settings.APP_MODE = AppMode.SERVER
    with Session(get_engine()) as session:
        user = User(email="server@example.com", full_name="Server", hashed_password="disabled")
        session.add(user)
        session.commit()
        session.refresh(user)
        session.add(EventRaw(
            event_type="clipboard",
            session_id="legacy-session",
            payload_json='{"text":"Legacy event without an owner must not leak."}',
            hash="legacy-event",
            source="clipboard",
        ))
        session.commit()
        events = load_unprocessed_events(session, int(user.id))

    assert events == []
