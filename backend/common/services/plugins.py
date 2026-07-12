from __future__ import annotations

import json

from sqlmodel import Session, select

from backend.common.models.schemas import PluginManifestRequest
from backend.common.models.sql import (
    OrganizationMembership,
    PluginGrant,
    PluginInstallation,
    Workspace,
    WorkspaceMembership,
)


def install_plugin(
    session: Session,
    *,
    organization_id: int,
    workspace_id: int | None,
    actor_user_id: int,
    manifest: PluginManifestRequest,
) -> PluginInstallation:
    if not _is_admin(session, organization_id, workspace_id, actor_user_id):
        raise PermissionError("Plugin administration permission required")
    if workspace_id is not None:
        workspace = session.get(Workspace, workspace_id)
        if workspace is None or workspace.organization_id != organization_id:
            raise ValueError("Workspace does not belong to organization")
    installation = PluginInstallation(
        organization_id=organization_id,
        workspace_id=workspace_id,
        plugin_key=manifest.plugin_key,
        version=manifest.version,
        manifest_json=manifest.model_dump_json(),
        installed_by_user_id=actor_user_id,
    )
    session.add(installation)
    try:
        session.commit()
        session.refresh(installation)
    except Exception:
        session.rollback()
        raise ValueError("Plugin is already installed for this scope")
    return installation


def grant_plugin_capability(
    session: Session,
    *,
    installation_id: int,
    actor_user_id: int,
    capability: str,
    target: str,
) -> PluginGrant:
    installation = session.get(PluginInstallation, installation_id)
    if installation is None:
        raise ValueError("Plugin installation not found")
    if not _is_admin(session, installation.organization_id, installation.workspace_id, actor_user_id):
        raise PermissionError("Plugin administration permission required")
    manifest = json.loads(installation.manifest_json)
    if capability not in manifest.get("requested_capabilities", []):
        raise ValueError("Capability was not requested by the plugin manifest")
    grant = PluginGrant(
        installation_id=installation_id,
        capability=capability,
        target=target,
        granted_by_user_id=actor_user_id,
    )
    session.add(grant)
    try:
        session.commit()
        session.refresh(grant)
    except Exception:
        session.rollback()
        raise ValueError("Plugin capability grant already exists")
    return grant


def _is_admin(session: Session, organization_id: int, workspace_id: int | None, user_id: int) -> bool:
    organization = session.exec(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.user_id == user_id,
            OrganizationMembership.role == "organization_admin",
            OrganizationMembership.is_active,
        )
    ).first()
    if organization is not None:
        return True
    if workspace_id is None:
        return False
    workspace_admin = session.exec(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_id == user_id,
            WorkspaceMembership.role == "workspace_admin",
            WorkspaceMembership.is_active,
        )
    ).first()
    return workspace_admin is not None
