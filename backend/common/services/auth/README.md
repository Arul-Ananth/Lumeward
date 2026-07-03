# Auth Architecture

## Current shape

- `trusted_lan` provider creates or resolves one synthetic LAN identity and bypasses browser login.
- `interactive` provider uses password credentials plus server-stored opaque sessions.
- Business routes depend on `AuthPrincipal`, not on the session transport directly.

## Main modules

- `store.py`: identity lookup, user creation, and session token persistence.
- `resolver.py`: route-facing auth resolution.
- `providers/trusted_lan.py`: trusted-LAN principal creation.
- `providers/interactive.py`: signup, login, and session-backed request resolution.
- `transports.py`: current bearer-session extraction.

## Extension path

To add another auth system later:

1. add a provider module that can resolve or create identities,
2. add a transport adapter if the new flow uses a different request transport,
3. keep route handlers unchanged by returning the same `AuthPrincipal` shape.
