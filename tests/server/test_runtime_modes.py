from backend.common.config import AppMode, AuthMode, Settings


def test_shared_auth_mode_is_canonical_with_legacy_alias() -> None:
    settings = Settings(APP_MODE=AppMode.SERVER, AUTH_MODE="shared", TRUSTED_LAN_MODE=False)
    assert settings.auth_mode() is AuthMode.SHARED

    legacy = Settings(APP_MODE=AppMode.SERVER, AUTH_MODE="trusted_lan", TRUSTED_LAN_MODE=False)
    assert legacy.auth_mode() is AuthMode.SHARED


def test_desktop_always_uses_shared_auth() -> None:
    settings = Settings(APP_MODE=AppMode.DESKTOP, AUTH_MODE="interactive", TRUSTED_LAN_MODE=False)
    assert settings.auth_mode() is AuthMode.SHARED
