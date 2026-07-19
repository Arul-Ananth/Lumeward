from sqlmodel import Session, select

from backend.common.database import get_engine
from backend.common.config import AppMode, settings
from backend.common.models.sql import (
    ContextItem, ContextTag, EventRaw, Organization, OrganizationMembership,
    Tag, User, Workspace, WorkspaceMembership,
)
from backend.common.services.ingestion import text_context
from backend.common.services.intelligence_feed.feed_router import IntelligenceFeedRouter
from backend.common.services.tags import set_user_tag_preference


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
            source="manual",
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


def test_tagged_workspace_context_personalizes_each_members_feed(
    isolated_data_dir, fake_embedder, fake_qdrant, monkeypatch
) -> None:
    monkeypatch.setattr(text_context, "ensure_collection", lambda _name: None)
    monkeypatch.setattr(text_context, "get_embedder", lambda: fake_embedder)
    monkeypatch.setattr(text_context, "client", fake_qdrant)
    settings.APP_MODE = AppMode.SERVER
    with Session(get_engine()) as session:
        owner = User(email="feed-owner@example.com", full_name="Owner", hashed_password="disabled")
        member = User(email="feed-member@example.com", full_name="Member", hashed_password="disabled")
        organization = Organization(name="Feed Org", slug="feed-org")
        session.add_all([owner, member, organization])
        session.commit()
        session.refresh(owner)
        session.refresh(member)
        session.refresh(organization)
        workspace = Workspace(organization_id=organization.id, name="Team", slug="team")
        tag = Tag(organization_id=organization.id, normalized_key="security", display_name="Security")
        session.add_all([workspace, tag])
        session.commit()
        session.refresh(workspace)
        session.refresh(tag)
        session.add_all([
            OrganizationMembership(organization_id=organization.id, user_id=owner.id, role="organization_admin"),
            OrganizationMembership(organization_id=organization.id, user_id=member.id, role="member"),
            WorkspaceMembership(workspace_id=workspace.id, user_id=owner.id, role="workspace_admin"),
            WorkspaceMembership(workspace_id=workspace.id, user_id=member.id, role="member"),
        ])
        session.commit()
        text_context.ingest_workspace_text(
            session,
            text="A security incident affects the team deployment process.",
            source="web",
            title="Security deployment incident requiring team review",
            user_id=owner.id,
            organization_id=organization.id,
            workspace_id=workspace.id,
            tag_ids=[tag.id],
        )
        assert session.exec(select(ContextTag)).one().tag_id == tag.id
        set_user_tag_preference(session, user_id=member.id, tag_id=tag.id, weight=0, muted=True)

        router = IntelligenceFeedRouter()
        scope = {"workspace_ids": (workspace.id,), "organization_ids": (organization.id,)}
        assert router.process_new_events(session, owner.id, **scope) == 1
        assert router.process_new_events(session, member.id, **scope) == 0
        assert len(router.list_cards(session, owner.id)) == 1
        assert router.list_cards(session, member.id) == []
