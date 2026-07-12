from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from sqlmodel import Session

from backend.common.config import AuthMode, settings
from backend.common.database import get_session
from backend.common.services.auth.providers.interactive import resolve_interactive_context
from backend.common.services.auth.providers.trusted_lan import resolve_trusted_lan_context
from backend.common.services.auth.transports import extract_bearer_token
from backend.common.services.auth.types import AuthContext, AuthPrincipal
from backend.common.services.authorization import RequestContext, build_request_context, workspace_header


def get_auth_context(
    request: Request,
    session: Session = Depends(get_session),
) -> AuthContext:
    if settings.auth_mode() == AuthMode.TRUSTED_LAN:
        return resolve_trusted_lan_context(session)
    return resolve_interactive_context(session, extract_bearer_token(request))


def get_current_principal(
    auth_context: AuthContext = Depends(get_auth_context),
) -> AuthPrincipal:
    if auth_context.principal is None or not auth_context.authenticated:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return auth_context.principal


def get_request_context(
    workspace_id: int | None = Depends(workspace_header),
    auth_context: AuthContext = Depends(get_auth_context),
    session: Session = Depends(get_session),
) -> RequestContext:
    principal = get_current_principal(auth_context)
    return build_request_context(session, principal, workspace_id)
