from __future__ import annotations

import importlib.util
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from backend.common.config import AppMode, settings
from backend.common.version import APP_VERSION


def _ok(message: str) -> tuple[str, bool]:
    return message, True


def _fail(message: str) -> tuple[str, bool]:
    return message, False


def _check_python() -> tuple[str, bool]:
    version = sys.version_info
    if version >= (3, 11):
        return _ok(f"Python {version.major}.{version.minor}.{version.micro}")
    return _fail(f"Python {version.major}.{version.minor}.{version.micro}; Python 3.11+ required")


def _check_executable(name: str) -> tuple[str, bool]:
    found = shutil.which(name)
    return _ok(f"{name}: {found}") if found else _fail(f"{name}: not found")


def _check_module(name: str) -> tuple[str, bool]:
    return _ok(f"module {name}: available") if importlib.util.find_spec(name) else _fail(f"module {name}: missing")


def _check_env_file() -> tuple[str, bool]:
    env_path = ROOT / ".env"
    if env_path.exists():
        return _ok(".env: present")
    return _fail(".env: missing; copy .env.example and configure it")


def _check_qdrant_lock() -> tuple[str, bool]:
    lock_path = settings.DATA_DIR / "qdrant_db" / ".lock"
    if not lock_path.exists():
        return _ok("Qdrant local lock: clear")
    try:
        import portalocker

        with lock_path.open("a+") as handle:
            portalocker.lock(handle, portalocker.LOCK_EX | portalocker.LOCK_NB)
            portalocker.unlock(handle)
        return _ok("Qdrant local lock: present but not held")
    except Exception as exc:
        return _fail(f"Qdrant local lock: locked or unavailable ({exc})")


def _check_desktop_platform_notes() -> list[tuple[str, bool]]:
    checks: list[tuple[str, bool]] = []
    if settings.APP_MODE != AppMode.DESKTOP:
        return checks
    if sys.platform.startswith("linux"):
        checks.append(_check_module("keyring"))
        checks.append(_check_module("secretstorage"))
    elif sys.platform == "darwin":
        checks.append(_ok("macOS: protected folders may require user approval at runtime"))
    elif sys.platform == "win32":
        checks.append(_ok("Windows: per-user install recommended; no admin rights required for normal app data"))
    return checks


def run_checks() -> list[tuple[str, bool]]:
    checks = [
        _ok(f"Lumeward version: {APP_VERSION}"),
        _check_python(),
        _check_env_file(),
        _check_executable("npm"),
        _check_module("PyInstaller"),
        _check_qdrant_lock(),
    ]
    checks.extend(_check_desktop_platform_notes())
    if settings.ENGINE_ENABLED and not settings.engine_base_url():
        checks.append(_fail("ENGINE_ENABLED=true but ENGINE_BASE_URL is empty"))
    if settings.APP_MODE == AppMode.SERVER and not settings.is_trusted_lan_auth() and not settings.SECRET_KEY:
        checks.append(_fail("interactive server mode requires SECRET_KEY"))
    return checks


def main() -> int:
    print("Lumeward Beta 1.0 preflight")
    print(f"Data dir: {settings.DATA_DIR}")
    failed = False
    for message, passed in run_checks():
        status = "OK" if passed else "FAIL"
        print(f"[{status}] {message}")
        failed = failed or not passed
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
