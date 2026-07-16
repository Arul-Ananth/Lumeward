# Architecture Overview

Current release target: `1.0.0-beta.1`.

Lumeward has a shared Python service core, a FastAPI server, a PySide desktop
client and a React web client. `backend/main.py` resolves CLI overrides,
environment configuration and defaults.

## Runtime boundaries

- Local desktop: SQLite, embedded Qdrant, fixed local identity and native OS capabilities.
- Enterprise desktop: local UI/preferences plus authenticated requests to a selected server workspace.
- Server: PostgreSQL, external or bundled native Qdrant, authentication and shared business APIs.
- React: browser client for the server API; it does not replace native desktop capabilities.

## Enterprise domain

The relational model includes users, organizations, workspaces, organization
and workspace memberships, tags, personal tag preferences, workspace tag
policies, context items, organization invitations, organization audit events,
retention-policy metadata, plugin installations and plugin grants.

Authenticated requests resolve a principal and an allowed request scope.
`X-Workspace-ID` selects an active workspace. SQL event reads and Qdrant vector
queries apply user/workspace/organization filters before content reaches the
generation pipeline.

Plugin manifests and independent capability grants are a future-facing
foundation only. There is no plugin execution runtime or plugin context ingestion.

## Storage

- Desktop uses local SQLite and embedded Qdrant.
- Server requires an existing PostgreSQL database and role.
- Server startup creates missing tables and idempotently reconciles the four
  event-ownership columns, their indexes and the one-active-organization-
  membership partial index, without schema versioning.
- Server Qdrant can be external or a configured bundled native executable.
- Staged ZIP uploads are temporary; indexed SQL and Qdrant state persists.

## Service boundaries

- `auth/`: identities, sessions and request principals.
- `authorization.py`: organization/workspace membership and request scopes.
- `organization_setup.py`: atomic organization signup and first-session creation.
- `admin_common.py`, `admin_queries.py`, `membership_admin.py`, `invitations.py`
  and `tag_admin.py`: organization-administration queries and mutations.
- `newsletter/`: typed generation request, templates, persistence and schedules.
- `memory/`: scoped Qdrant retrieval and feedback/profile memory.
- `ingestion/`: files, ZIP uploads and workspace text ingestion.
- `intelligence_feed/`: event normalization, scoring and feed cards.
- `tags.py`: tag creation and personal/workspace policy.
- `plugins.py`: metadata installations and grants only.
- `telemetry/`: consented desktop collection and event processing.

## Web administration flow

In interactive mode, web signup creates the user, password identity,
organization, active organization-administrator membership, audit record and
session in one transaction. The organization is active immediately and its slug
is generated server-side. The administrator must then create the first
workspace before entering `/admin/overview`.

The React client separates organization administration under `/admin/*` from
briefings and personal features under `/workspace`. Organization administrators
can manage the whole organization. Workspace administrators can see only their
assigned workspace members, shared context and tag policies. Ordinary members
do not receive administration navigation.

Invitations use random, single-use tokens stored only as hashes. New users set a
name and password during acceptance; existing users must sign in with the
invited email. SMTP delivery is optional because every create/resend response
also supplies a copyable invitation link.

## Desktop enterprise flow

The user configures a server URL, signs up or signs in, receives an opaque
session token, loads authorized workspaces and selects one. Generation runs on
the server. File drops and bridge content can be explicitly shared; clipboard
text requires all privacy opt-ins. Local feed processing is disabled while
connected to an enterprise server.

## Current limitations

- Production identity federation and centralized provisioning are not implemented.
- Authentication is limited to email/password sessions. OIDC, email
  verification, password reset, social login and MFA are not implemented.
- The administration portal does not manage billing, infrastructure, secrets,
  plugins, retention, custom roles or organization deletion.
- Plugin execution, plugin secrets and plugin ingestion are deferred.
- PostgreSQL reconciliation covers the ownership and active-membership deltas
  introduced in this release, not arbitrary future model changes.
- Public exposure still requires TLS, a reverse proxy and operational hardening.
