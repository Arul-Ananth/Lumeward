# Organization Administration Portal Handoff

## Product outcome

The current working tree reframes the web client as an organization
administration portal while retaining briefings, feeds, memory and private user
activity in `/workspace`.

An administrator can register an organization, receive an immediate session,
create the required first workspace, invite people, manage organization and
workspace access, share workspace context, manage tag policies, rename the
organization/workspaces and inspect administration activity.

## Deliberate scope

Included:

- atomic organization signup and immediate activation;
- email/password login through the existing bearer-session system;
- required first-workspace onboarding;
- organization-admin, workspace-admin and member behavior;
- invitations with optional SMTP delivery and mandatory copy-link fallback;
- people, workspaces, shared context, settings and audit screens;
- one active organization membership per account;
- last-active-organization-administrator protection;
- session revocation when a member is deactivated.

Excluded:

- OIDC, social login, email verification, password reset, remember-me and MFA;
- billing, organization deletion, custom roles and retention controls;
- infrastructure, database, model-secret and plugin administration;
- plugin execution and plugin-driven ingestion.

## Backend shape

`backend/server/routers/admin.py` is the dedicated `/admin` API surface. It
provides bootstrap/overview, organization settings, workspaces, members,
invitations, shared context, tags/policies and audit history.

`backend/server/routers/auth.py` adds atomic `/auth/organization-signup` plus
invitation inspection and acceptance. `/auth/signup` and the older
organization/workspace APIs remain for desktop/API compatibility.

The administration services are intentionally split by responsibility:

- `backend/common/services/organization_setup.py`
- `backend/common/services/admin_common.py`
- `backend/common/services/admin_queries.py`
- `backend/common/services/membership_admin.py`
- `backend/common/services/invitations.py`
- `backend/common/services/invitation_mail.py`
- `backend/common/services/tag_admin.py`
- `backend/common/services/organization_admin.py` as a compatibility facade

New relational records live in `backend/common/models/sql.py`:

- `OrganizationInvitation`;
- `InvitationWorkspaceAssignment`;
- `OrganizationAuditEvent`.

Invitation tokens are random, stored only as hashes, single-use and expire after
`INVITATION_EXPIRE_DAYS` (seven days by default). Resending replaces the token.
Email failure does not roll back the invitation. The raw link is returned only
when creating or resending because it cannot be reconstructed later.

PostgreSQL enforces one active organization membership per user with the partial
unique index `uq_org_membership_one_active_per_user`; startup reconciles this
index for existing server databases.

## Frontend shape

`frontend/src/App.tsx` owns these route boundaries:

- `/signup`, `/signin`;
- `/invite/:token`;
- `/onboarding/workspace`;
- `/admin/overview`;
- `/admin/people`;
- `/admin/workspaces`;
- `/admin/context`;
- `/admin/settings`;
- `/admin/audit`;
- `/workspace`.

Administration code is grouped under `frontend/src/features/admin/`. The
responsive shell shows organization, workspace scope, role, navigation and the
account menu. Organization administrators see every admin section. Workspace
administrators see People and Shared Context for assigned workspaces. Members
are directed to `/workspace`.

Server state stays in feature APIs/hooks and the small admin context. No general
global-state dependency was introduced. Shared loading, empty and error states
are in `frontend/src/features/admin/components/`.

## Configuration

`.env.example` documents:

- `FRONTEND_PUBLIC_URL`;
- `INVITATION_EXPIRE_DAYS`;
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`;
- `SMTP_FROM_EMAIL`, `SMTP_USE_TLS`, `SMTP_USE_SSL`;
- `SMTP_TIMEOUT_SECONDS`.

SMTP is optional for development. `FRONTEND_PUBLIC_URL` must be reachable by the
invite recipient and must match the deployed frontend origin.

## Known limitations and follow-up

- The session token remains in browser `sessionStorage`; the deployment is not
  a reviewed public-internet profile.
- Audit rows are application history, not immutable/tamper-evident compliance
  records, and retention/export controls are not implemented.
- SMTP has no provider-specific bounce, retry or abuse-management integration.
- Existing PostgreSQL deployments use create-if-missing tables plus a small
  idempotent compatibility reconciliation, not a general schema-version system.
- Automated frontend coverage is currently focused rather than exhaustive.
- A real visual browser walkthrough is still required; the in-app browser was
  unavailable during the last verification session.

The original UI assessment is retained at
`../audits/web_admin_ui_review_2026-07-15.md` as historical decision context.
