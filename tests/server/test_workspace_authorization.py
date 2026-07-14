import pytest
from fastapi import HTTPException
from sqlmodel import Session

from backend.common.database import get_engine
from backend.common.models.sql import Organization, OrganizationMembership, User, Workspace, WorkspaceMembership
from backend.common.services.auth.types import AuthPrincipal
from backend.common.services.authorization import (
    add_organization_member,
    build_request_context,
    create_organization_for_user,
    create_workspace,
    require_workspace_role,
)
from backend.common.services.tags import create_tag, set_user_tag_preference, set_workspace_tag_policy
from backend.common.models.schemas import PluginManifestRequest
from backend.common.services.plugins import grant_plugin_capability, install_plugin


def test_request_context_only_contains_active_memberships(isolated_data_dir) -> None:
    with Session(get_engine()) as session:
        user = User(email="member@example.com", full_name="Member", hashed_password="disabled")
        outsider = User(email="outsider@example.com", full_name="Outsider", hashed_password="disabled")
        session.add(user)
        session.add(outsider)
        session.commit()
        session.refresh(user)
        session.refresh(outsider)

        organization = Organization(name="Example", slug="example")
        session.add(organization)
        session.commit()
        session.refresh(organization)
        workspace = Workspace(organization_id=organization.id, name="Engineering", slug="engineering")
        session.add(workspace)
        session.commit()
        session.refresh(workspace)
        session.add_all([
            OrganizationMembership(organization_id=organization.id, user_id=user.id, role="member"),
            WorkspaceMembership(workspace_id=workspace.id, user_id=user.id, role="member"),
            OrganizationMembership(organization_id=organization.id, user_id=outsider.id, role="member", is_active=False),
        ])
        session.commit()

        principal = AuthPrincipal(
            user_id=user.id,
            identity_id=1,
            provider="test",
            subject="member@example.com",
            auth_mode="interactive",
            transport="test",
            user=user,
        )
        context = build_request_context(session, principal, workspace.id)
        assert context.organization_ids == (organization.id,)
        assert context.workspace_ids == (workspace.id,)
        assert context.active_workspace_id == workspace.id


def test_request_context_rejects_non_member_workspace(isolated_data_dir) -> None:
    with Session(get_engine()) as session:
        user = User(email="nonmember@example.com", full_name="Nonmember", hashed_password="disabled")
        session.add(user)
        session.commit()
        session.refresh(user)
        organization = Organization(name="Private", slug="private")
        session.add(organization)
        session.commit()
        session.refresh(organization)
        workspace = Workspace(organization_id=organization.id, name="Restricted", slug="restricted")
        session.add(workspace)
        session.commit()
        session.refresh(workspace)
        principal = AuthPrincipal(
            user_id=user.id,
            identity_id=1,
            provider="test",
            subject="nonmember@example.com",
            auth_mode="interactive",
            transport="test",
            user=user,
        )
        with pytest.raises(HTTPException) as error:
            build_request_context(session, principal, workspace.id)
        assert error.value.status_code == 403


def test_workspace_role_does_not_leak_from_another_workspace(isolated_data_dir) -> None:
    with Session(get_engine()) as session:
        user = User(email="roles@example.com", full_name="Roles", hashed_password="disabled")
        organization = Organization(name="Roles Org", slug="roles-org")
        session.add_all([user, organization])
        session.commit()
        session.refresh(user)
        session.refresh(organization)
        admin_workspace = Workspace(organization_id=organization.id, name="Admin", slug="admin")
        member_workspace = Workspace(organization_id=organization.id, name="Member", slug="member")
        session.add_all([admin_workspace, member_workspace])
        session.commit()
        session.refresh(admin_workspace)
        session.refresh(member_workspace)
        session.add_all([
            OrganizationMembership(organization_id=organization.id, user_id=user.id, role="member"),
            WorkspaceMembership(workspace_id=admin_workspace.id, user_id=user.id, role="workspace_admin"),
            WorkspaceMembership(workspace_id=member_workspace.id, user_id=user.id, role="member"),
        ])
        session.commit()
        principal = AuthPrincipal(
            user_id=user.id,
            identity_id=1,
            provider="test",
            subject="roles@example.com",
            auth_mode="interactive",
            transport="test",
            user=user,
        )

        admin_context = build_request_context(session, principal, admin_workspace.id)
        require_workspace_role(admin_context, "workspace_admin")

        member_context = build_request_context(session, principal, member_workspace.id)
        with pytest.raises(HTTPException) as error:
            require_workspace_role(member_context, "workspace_admin")
        assert error.value.status_code == 403


def test_request_context_exposes_only_selected_workspace(isolated_data_dir) -> None:
    with Session(get_engine()) as session:
        user = User(email="scope@example.com", full_name="Scope", hashed_password="disabled")
        session.add(user)
        session.commit()
        session.refresh(user)
        first_org = create_organization_for_user(session, user_id=user.id, name="First", slug="first")
        first = create_workspace(
            session, organization_id=first_org.id, actor_user_id=user.id, name="First", slug="first"
        )
        second_org = Organization(name="Second", slug="second")
        session.add(second_org)
        session.commit()
        session.refresh(second_org)
        second = Workspace(organization_id=second_org.id, name="Second", slug="second")
        session.add(second)
        session.commit()
        session.refresh(second)
        session.add_all([
            OrganizationMembership(organization_id=second_org.id, user_id=user.id, role="member"),
            WorkspaceMembership(workspace_id=second.id, user_id=user.id, role="member"),
        ])
        session.commit()
        principal = AuthPrincipal(
            user_id=user.id, identity_id=1, provider="test", subject=user.email,
            auth_mode="interactive", transport="test", user=user,
        )

        selected = build_request_context(session, principal, first.id)
        assert selected.workspace_ids == (first.id,)
        assert selected.organization_ids == (first_org.id,)
        assert build_request_context(session, principal).workspace_ids == ()
        assert build_request_context(session, principal).organization_ids == ()


def test_organization_admin_enrolls_existing_user(isolated_data_dir) -> None:
    with Session(get_engine()) as session:
        owner = User(email="org-owner@example.com", full_name="Owner", hashed_password="disabled")
        member = User(email="org-member@example.com", full_name="Member", hashed_password="disabled")
        session.add_all([owner, member])
        session.commit()
        session.refresh(owner)
        organization = create_organization_for_user(session, user_id=owner.id, name="Org", slug="org")

        membership = add_organization_member(
            session, organization_id=organization.id, actor_user_id=owner.id,
            email=member.email, role="member",
        )
        assert membership.user_id == member.id
        assert membership.role == "member"


def test_user_can_bootstrap_one_organization_and_workspace_admin_can_create_workspace(isolated_data_dir) -> None:
    with Session(get_engine()) as session:
        user = User(email="owner@example.com", full_name="Owner", hashed_password="disabled")
        session.add(user)
        session.commit()
        session.refresh(user)
        organization = create_organization_for_user(
            session,
            user_id=user.id,
            name="Acme",
            slug="acme",
        )
        workspace = create_workspace(
            session,
            organization_id=organization.id,
            actor_user_id=user.id,
            name="Platform",
            slug="platform",
        )
        assert workspace.organization_id == organization.id


def test_non_member_cannot_create_workspace(isolated_data_dir) -> None:
    with Session(get_engine()) as session:
        owner = User(email="owner2@example.com", full_name="Owner", hashed_password="disabled")
        outsider = User(email="outsider2@example.com", full_name="Outsider", hashed_password="disabled")
        session.add(owner)
        session.add(outsider)
        session.commit()
        session.refresh(owner)
        session.refresh(outsider)
        organization = create_organization_for_user(session, user_id=owner.id, name="Acme Two", slug="acme-two")
        with pytest.raises(PermissionError):
            create_workspace(
                session,
                organization_id=organization.id,
                actor_user_id=outsider.id,
                name="Restricted",
                slug="restricted",
            )


def test_tag_preferences_and_workspace_policy_are_scoped(isolated_data_dir) -> None:
    with Session(get_engine()) as session:
        user = User(email="tag-owner@example.com", full_name="Tag Owner", hashed_password="disabled")
        session.add(user)
        session.commit()
        session.refresh(user)
        organization = create_organization_for_user(session, user_id=user.id, name="Tagged", slug="tagged")
        workspace = create_workspace(
            session,
            organization_id=organization.id,
            actor_user_id=user.id,
            name="Research",
            slug="research",
        )
        tag = create_tag(session, organization_id=organization.id, display_name="Incident Response")
        preference = set_user_tag_preference(
            session,
            user_id=user.id,
            tag_id=tag.id,
            weight=0.8,
            muted=False,
        )
        policy = set_workspace_tag_policy(
            session,
            workspace_id=workspace.id,
            actor_user_id=user.id,
            tag_id=tag.id,
            priority=1.0,
            blocked=False,
        )
        assert preference.weight == 0.8
        assert policy.priority == 1.0


def test_plugin_capability_requires_manifest_request_and_admin(isolated_data_dir) -> None:
    with Session(get_engine()) as session:
        user = User(email="plugin-owner@example.com", full_name="Plugin Owner", hashed_password="disabled")
        session.add(user)
        session.commit()
        session.refresh(user)
        organization = create_organization_for_user(session, user_id=user.id, name="Plugins", slug="plugins")
        installation = install_plugin(
            session,
            organization_id=organization.id,
            workspace_id=None,
            actor_user_id=user.id,
            manifest=PluginManifestRequest(
                plugin_key="rss",
                version="1.0.0",
                requested_capabilities=["network:origin"],
                allowed_network_origins=["https://example.com"],
                context_types=["article"],
            ),
        )
        grant = grant_plugin_capability(
            session,
            installation_id=installation.id,
            actor_user_id=user.id,
            capability="network:origin",
            target="https://example.com",
        )
        assert grant.active is True
