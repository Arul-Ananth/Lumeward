from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta

from sqlmodel import Session, select

from backend.common.config import settings
from backend.common.models.sql import AuthIdentity, AuthSession, User
from backend.common.services.auth.auth_utils import get_password_hash

INTERACTIVE_PROVIDER = "interactive_password"
TRUSTED_LAN_PROVIDER = "trusted_lan"
DESKTOP_LOCAL_PROVIDER = "desktop_local"
SESSION_TRANSPORT = "bearer_session"


def _normalize_subject(value: str) -> str:
    return value.strip().lower()


def hash_session_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def get_user_by_email(session: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email.strip().lower())
    return session.exec(statement).first()


def get_identity_by_provider_subject(session: Session, provider: str, subject: str) -> AuthIdentity | None:
    statement = select(AuthIdentity).where(
        AuthIdentity.provider == provider,
        AuthIdentity.subject == _normalize_subject(subject),
    )
    return session.exec(statement).first()


def get_identity_by_email(session: Session, provider: str, email: str) -> AuthIdentity | None:
    statement = select(AuthIdentity).where(
        AuthIdentity.provider == provider,
        AuthIdentity.email == email.strip().lower(),
    )
    return session.exec(statement).first()


def ensure_identity(
    session: Session,
    *,
    user: User,
    provider: str,
    subject: str,
    email: str | None = None,
    password_hash: str | None = None,
    is_synthetic: bool = False,
) -> AuthIdentity:
    identity = get_identity_by_provider_subject(session, provider, subject)
    if identity is not None:
        updated = False
        if email and identity.email != email.strip().lower():
            identity.email = email.strip().lower()
            updated = True
        if password_hash and identity.password_hash != password_hash:
            identity.password_hash = password_hash
            updated = True
        if updated:
            identity.updated_at = datetime.utcnow()
            session.add(identity)
            session.commit()
            session.refresh(identity)
        return identity

    identity = AuthIdentity(
        user_id=user.id,
        provider=provider,
        subject=_normalize_subject(subject),
        email=email.strip().lower() if email else None,
        password_hash=password_hash,
        is_synthetic=is_synthetic,
    )
    session.add(identity)
    session.commit()
    session.refresh(identity)
    return identity


def create_user_with_password_identity(
    session: Session,
    *,
    full_name: str,
    email: str,
    password: str,
) -> tuple[User, AuthIdentity]:
    normalized_email = email.strip().lower()
    if get_user_by_email(session, normalized_email):
        raise ValueError("Email exists")

    password_hash = get_password_hash(password)
    user = User(
        email=normalized_email,
        full_name=full_name.strip(),
        hashed_password=password_hash,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    identity = ensure_identity(
        session,
        user=user,
        provider=INTERACTIVE_PROVIDER,
        subject=normalized_email,
        email=normalized_email,
        password_hash=password_hash,
    )
    return user, identity


def ensure_trusted_lan_user(session: Session) -> tuple[User, AuthIdentity]:
    user = get_user_by_email(session, settings.TRUSTED_LAN_USER_EMAIL)
    if user is None:
        user = User(
            email=settings.TRUSTED_LAN_USER_EMAIL,
            full_name=settings.TRUSTED_LAN_USER_NAME,
            hashed_password=get_password_hash("disabled"),
        )
        session.add(user)
        session.commit()
        session.refresh(user)
    identity = ensure_identity(
        session,
        user=user,
        provider=TRUSTED_LAN_PROVIDER,
        subject=settings.TRUSTED_LAN_USER_EMAIL,
        email=settings.TRUSTED_LAN_USER_EMAIL,
        password_hash=user.hashed_password,
        is_synthetic=True,
    )
    return user, identity


def ensure_desktop_local_user(
    session: Session,
    *,
    email: str,
    full_name: str,
) -> tuple[User, AuthIdentity]:
    user = get_user_by_email(session, email)
    if user is None:
        user = User(
            email=email,
            full_name=full_name,
            hashed_password=get_password_hash("disabled"),
        )
        session.add(user)
        session.commit()
        session.refresh(user)
    identity = ensure_identity(
        session,
        user=user,
        provider=DESKTOP_LOCAL_PROVIDER,
        subject=email,
        email=email,
        password_hash=user.hashed_password,
        is_synthetic=True,
    )
    return user, identity


def create_session_token(session: Session, *, user: User, identity: AuthIdentity) -> str:
    raw_token = secrets.token_urlsafe(32)
    now = datetime.utcnow()
    auth_session = AuthSession(
        user_id=user.id,
        identity_id=identity.id,
        transport=SESSION_TRANSPORT,
        token_hash=hash_session_token(raw_token),
        expires_at=now + timedelta(minutes=settings.AUTH_SESSION_EXPIRE_MINUTES),
        last_used_at=now,
    )
    session.add(auth_session)
    session.commit()
    return raw_token


def resolve_session_token(session: Session, raw_token: str) -> tuple[AuthSession, AuthIdentity, User] | None:
    token_hash = hash_session_token(raw_token)
    statement = select(AuthSession).where(AuthSession.token_hash == token_hash)
    auth_session = session.exec(statement).first()
    if auth_session is None or auth_session.revoked_at is not None or auth_session.expires_at < datetime.utcnow():
        return None

    identity = session.get(AuthIdentity, auth_session.identity_id)
    user = session.get(User, auth_session.user_id)
    if identity is None or user is None or not identity.is_active:
        return None

    auth_session.last_used_at = datetime.utcnow()
    session.add(auth_session)
    session.commit()
    return auth_session, identity, user


def revoke_session_token(session: Session, raw_token: str) -> None:
    token_hash = hash_session_token(raw_token)
    statement = select(AuthSession).where(AuthSession.token_hash == token_hash)
    auth_session = session.exec(statement).first()
    if auth_session is None:
        return
    auth_session.revoked_at = datetime.utcnow()
    session.add(auth_session)
    session.commit()
