"""Compatibility facade for focused organization-administration services.

New code should import from the focused modules. The facade keeps route and test
imports stable while the administration domain evolves.
"""

from backend.common.services.admin_common import (
    AdminScope,
    ORG_ADMIN,
    WORKSPACE_ADMIN,
    active_organization_membership,
    add_audit_event,
    get_admin_scope,
    slugify,
    unique_organization_slug,
    unique_workspace_slug,
    visible_workspaces,
)
from backend.common.services.admin_queries import (
    list_admin_tags,
    list_audit_events,
    list_shared_context,
    overview_counts,
)
from backend.common.services.invitations import (
    accept_invitation,
    effective_invitation_status,
    invitation_by_token,
    list_invitations,
    revoke_invitation,
    workspace_assignments_for_invitation,
)
from backend.common.services.membership_admin import list_members, update_member
from backend.common.services.organization_setup import (
    _new_session as _setup_new_session,
    create_admin_workspace,
    rename_organization,
    rename_workspace,
    signup_organization as _signup_organization,
)
from backend.common.services import invitations as _invitations
from backend.common.services.invitation_mail import send_invitation_email

# Kept for the current serializers; callers should prefer the public name.
_workspace_assignments_for_invitation = workspace_assignments_for_invitation
_new_session = _setup_new_session


def signup_organization(session, request):
    return _signup_organization(session, request, new_session=_new_session)


def create_invitation(session, scope, request):
    return _invitations.create_invitation(session, scope, request, deliver=send_invitation_email)


def resend_invitation(session, scope, invitation_id):
    return _invitations.resend_invitation(
        session,
        scope,
        invitation_id,
        deliver=send_invitation_email,
    )

__all__ = [
    "AdminScope",
    "ORG_ADMIN",
    "WORKSPACE_ADMIN",
    "_workspace_assignments_for_invitation",
    "_new_session",
    "accept_invitation",
    "active_organization_membership",
    "add_audit_event",
    "create_admin_workspace",
    "create_invitation",
    "effective_invitation_status",
    "get_admin_scope",
    "invitation_by_token",
    "list_admin_tags",
    "list_audit_events",
    "list_invitations",
    "list_members",
    "list_shared_context",
    "overview_counts",
    "rename_organization",
    "rename_workspace",
    "resend_invitation",
    "revoke_invitation",
    "signup_organization",
    "send_invitation_email",
    "slugify",
    "unique_organization_slug",
    "unique_workspace_slug",
    "update_member",
    "visible_workspaces",
    "workspace_assignments_for_invitation",
]
