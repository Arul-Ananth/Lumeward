# Security Notes

Lumeward is currently intended for local desktop use and internally managed
enterprise deployments. It is not internet-ready without normal infrastructure
hardening.

## Identity

- `AUTH_MODE=interactive` gives each server user an individual identity and opaque bearer session.
- `AUTH_MODE=shared` uses one synthetic identity. The legacy `trusted_lan` value remains accepted.
- Shared mode is unsuitable for individual audit, revocation or team boundaries.
- Interactive web signup immediately creates one organization and its first
  organization administrator. The older user-only signup API remains available
  temporarily for desktop compatibility.
- One account may have only one active organization membership. The service
  checks this rule and PostgreSQL enforces it with a partial unique index.
- The React client currently stores its session token in `sessionStorage`.

## Authorization and context

- Organization and workspace membership is checked server-side.
- Clients select a workspace with `X-Workspace-ID`.
- Event queries and Qdrant retrieval apply user/workspace/organization filters.
- Enterprise desktop generation requires a selected workspace.
- File drops and browser-bridge sharing are explicit actions.
- Clipboard content requires telemetry, clipboard and raw-text consent.
- Retrieved context is untrusted input and never an authorization mechanism.
- Organization administrators control organization roles, active status and all
  workspace assignments. Workspace administrators can change assignments only
  inside the workspaces they administer.
- The final active organization administrator cannot be demoted or deactivated.
- Deactivating a member revokes that user's active sessions.

## Invitations and audit

- Invitation tokens are random, expire after seven days by default, are stored
  only as hashes and are single-use.
- Resending replaces the prior token; revocation and acceptance invalidate it.
- Existing users must authenticate as the invited email before acceptance.
- SMTP is optional. Delivery failure keeps the invitation valid and the admin UI
  presents its copyable link as a recovery path.
- Privileged organization mutations write organization audit events. Summaries
  exclude passwords, raw invitation tokens and other secrets.
- These application audit rows are operational history, not an immutable or
  tamper-evident compliance log.

## Storage

- Desktop storage is local SQLite plus embedded Qdrant.
- Server storage is PostgreSQL plus external or bundled Qdrant.
- Bundled Qdrant should bind to loopback, use an API key and use a dedicated data directory.
- Runtime Qdrant storage, `.env`, local databases and secret material are ignored by Git.
- Server startup reconciles ownership columns and the active-membership partial
  index, so the database role needs the corresponding DDL permissions during
  this pre-release phase.

## Existing safeguards

- Strict typed API schemas and opaque, revocable interactive sessions.
- Workspace membership validation and scoped SQL/vector retrieval.
- Loopback-only, token-protected desktop bridge.
- Opt-in telemetry with raw clipboard storage disabled by default.
- ZIP traversal, symlink, extension, file-count and size validation.
- Network/tool policy checks for supported external actions.
- Plugin grants are metadata only; no plugin code executes.

## Required operational controls

- TLS and a reverse proxy for network deployment.
- Strong generated secrets and rotation procedures.
- Least-privilege service accounts and restricted data directories.
- PostgreSQL/Qdrant backups, retention rules and restore testing.
- Central provisioning, deprovisioning and MFA before broad enterprise rollout.
- Audit retention/integrity, deletion/export and data-residency procedures
  appropriate to customer obligations.

## Deferred security work

- OIDC federation and group/role synchronization.
- Invitation delivery hardening, abuse controls, centralized provisioning and
  automated deprovisioning.
- Retention/deletion enforcement across SQL, Qdrant, backups and derived artifacts.
- Isolated plugin workers, plugin secrets and enforced egress/filesystem grants.
- A reviewed public-internet deployment profile.
