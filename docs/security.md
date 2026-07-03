# Security Notes

## Current Modes

Lumeward now supports two web auth modes.

- `AUTH_MODE=trusted_lan`
  - one synthetic LAN identity is resolved on the server
  - browser sign-in is bypassed
  - memory/profile state is shared for that trusted identity
- `AUTH_MODE=interactive`
  - sign-in/sign-up remain active
  - the server issues opaque session tokens
  - business routes resolve a normalized principal through the auth resolver

`TRUSTED_LAN_MODE` is still accepted as a backward-compatible fallback for older env files, but the preferred selector is `AUTH_MODE`.

## Trust Boundaries

- FastAPI server:
  - trusted-LAN mode is intended for private network use only
  - server storage requires PostgreSQL and a Qdrant service configured through
    `QDRANT_URL`; localhost is supported, while embedded fallback is rejected
  - interactive mode improves auth boundaries but still requires normal deployment hardening before public exposure
  - folder upload accepts explicit `.zip` archives only through authenticated `/news/ingest/folder`
- Desktop bridge:
  - loopback only
  - protected with a runtime-generated bridge token header
- External network tools:
  - network actions are filtered through a security policy layer
  - non-approved actions are denied and logged

## Current Safeguards

- Env-driven host, port, and CORS allowlist
- Typed request schemas with `extra="forbid"`
- Auth provider and transport separation for web identity resolution
- Server-stored opaque interactive sessions
- Trusted-LAN synthetic identity isolation from interactive identities
- Bridge token validation on `/ingest`
- Structured security-policy audit logging
- Clipboard collection opt-in
- Desktop telemetry disabled by default unless the user opts in
- Raw clipboard text disabled by default
- Tool/network policy checks before external search requests
- Server folder upload is disabled/enabled through `FOLDER_UPLOAD_ENABLED`.
- Folder upload staging is constrained to `DATA_DIR / FOLDER_UPLOAD_DIR`.
- `FOLDER_UPLOAD_DIR` must be relative and cannot escape `DATA_DIR`.
- Upload cleanup deletes only managed staging files on server startup when `FOLDER_UPLOAD_DELETE_ON_RESTART=true`.
- Upload validation rejects path traversal, absolute zip paths, symlinks,
  unsupported extensions, too many files, compressed archives larger than
  `FOLDER_UPLOAD_MAX_ARCHIVE_MB`, and archives that expand beyond
  `FOLDER_UPLOAD_MAX_EXPANDED_MB`.
- Uploaded source files are indexed into the active relational database and
  Qdrant; indexed state is not deleted by staging cleanup.
- The default compressed archive limit is 250 MB and the default expanded limit
  is 1000 MB; operators can lower or raise both values in `.env`.

## Deferred Items

These are still open future work, not removed from the architecture:

- alternative auth transports such as cookies or external IdPs
- per-user memory isolation improvements beyond the current shared trusted-LAN identity
- internet-facing reverse proxy and TLS deployment profile
- stronger session rotation and revocation controls

## Future Direction

When Lumeward moves beyond the current deployment profile, the next hardening steps should be:

1. provider-specific auth adapters for the chosen web auth system
2. per-user memory isolation across all web modes
3. reverse proxy + TLS
4. stronger session lifecycle controls and public exposure hardening
