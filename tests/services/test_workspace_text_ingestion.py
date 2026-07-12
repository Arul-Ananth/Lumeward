from sqlmodel import Session, select

from backend.common.database import get_engine
from backend.common.models.sql import ContextItem, EventRaw, User
from backend.common.services.ingestion import text_context


def test_workspace_text_is_indexed_with_workspace_ownership(isolated_data_dir, fake_embedder, fake_qdrant, monkeypatch) -> None:
    monkeypatch.setattr(text_context, "ensure_collection", lambda _name: None)
    monkeypatch.setattr(text_context, "get_embedder", lambda: fake_embedder)
    monkeypatch.setattr(text_context, "client", fake_qdrant)
    with Session(get_engine()) as session:
        user = User(email="owner@example.com", full_name="Owner", hashed_password="disabled")
        session.add(user)
        session.commit()
        session.refresh(user)
        chunks = text_context.ingest_workspace_text(
            session,
            text="A deployment incident affects the engineering team.",
            source="browser_bridge",
            title="Incident",
            user_id=user.id,
            organization_id=7,
            workspace_id=11,
        )
        event = session.exec(select(EventRaw)).one()
        context_item = session.exec(select(ContextItem)).one()

    assert chunks == 1
    assert event.workspace_id == "11"
    assert event.visibility == "workspace"
    assert context_item.workspace_id == "11"
    assert fake_qdrant.points[0].payload["workspace_id"] == "11"
