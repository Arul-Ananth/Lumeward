"""Compatibility exports for older server imports.

New code should import auth dependencies from
``backend.common.services.auth.resolver`` and auth store helpers from
``backend.common.services.auth.store``.
"""

from backend.common.services.auth.resolver import get_auth_context, get_current_principal
from backend.common.services.auth.store import ensure_trusted_lan_user

__all__ = ["ensure_trusted_lan_user", "get_auth_context", "get_current_principal"]
