"""Lifecycle support for a Qdrant executable bundled with a server installer."""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from threading import RLock
from urllib.request import urlopen

from backend.common.config import settings

_process: subprocess.Popen | None = None
_lock = RLock()


def start_bundled_qdrant() -> None:
    """Start only the Qdrant process owned by this Lumeward server process."""
    global _process
    if settings.QDRANT_MODE != "bundled":
        return
    with _lock:
        if _healthy():
            return
        if _process is not None and _process.poll() is None:
            raise RuntimeError("Bundled Qdrant is running but did not become healthy.")
        binary = bundled_qdrant_binary_path()
        config = bundled_qdrant_config_path()
        environment = os.environ.copy()
        storage_dir = bundled_qdrant_storage_path()
        storage_dir.mkdir(parents=True, exist_ok=True)
        environment["QDRANT__STORAGE__STORAGE_PATH"] = str(storage_dir)
        if settings.QDRANT_API_KEY:
            environment["QDRANT__SERVICE__API_KEY"] = settings.QDRANT_API_KEY
        _process = subprocess.Popen(
            [str(binary), "--config-path", str(config)],
            cwd=str(binary.parent),
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        _wait_until_healthy(_process)


def stop_bundled_qdrant() -> None:
    global _process
    with _lock:
        if _process is not None and _process.poll() is None:
            _process.terminate()
            try:
                _process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                _process.kill()
        _process = None


def bundled_qdrant_binary_path() -> Path:
    """Return the configured executable and fail with an actionable error."""
    configured = settings.BUNDLED_QDRANT_BINARY.strip()
    if not configured:
        suffix = ".exe" if sys.platform == "win32" else ""
        configured = str(Path(sys.executable).resolve().parent / "qdrant" / f"qdrant{suffix}")
    path = Path(configured).expanduser().resolve()
    if not path.is_file():
        raise RuntimeError(f"Bundled Qdrant executable was not found: {path}")
    return path


def bundled_qdrant_config_path() -> Path:
    """Return the configured Qdrant config file."""
    configured = settings.BUNDLED_QDRANT_CONFIG_PATH.strip()
    if not configured:
        raise RuntimeError("BUNDLED_QDRANT_CONFIG_PATH is required when QDRANT_MODE=bundled.")
    path = Path(configured).expanduser().resolve()
    if not path.is_file():
        raise RuntimeError(f"Bundled Qdrant configuration was not found: {path}")
    return path


def bundled_qdrant_storage_path() -> Path:
    """Return the server-owned Qdrant storage directory."""
    configured = settings.BUNDLED_QDRANT_STORAGE_DIR.strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return (settings.DATA_DIR / "qdrant-server").resolve()


def validate_bundled_qdrant_configuration() -> tuple[Path, Path, Path]:
    """Validate bundled paths without starting a process."""
    binary = bundled_qdrant_binary_path()
    config = bundled_qdrant_config_path()
    storage = bundled_qdrant_storage_path()
    parent = storage if storage.exists() else storage.parent
    if not parent.exists():
        raise RuntimeError(f"Bundled Qdrant storage parent does not exist: {parent}")
    if not os.access(parent, os.W_OK):
        raise RuntimeError(f"Bundled Qdrant storage is not writable: {parent}")
    return binary, config, storage


def _healthy() -> bool:
    try:
        with urlopen(f"{settings.QDRANT_URL.rstrip('/')}/healthz", timeout=1) as response:
            return 200 <= response.status < 300
    except OSError:
        return False


def _wait_until_healthy(process: subprocess.Popen) -> None:
    deadline = time.monotonic() + settings.BUNDLED_QDRANT_STARTUP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Bundled Qdrant exited with code {process.returncode}.")
        if _healthy():
            return
        time.sleep(0.2)
    stop_bundled_qdrant()
    raise RuntimeError("Bundled Qdrant did not become healthy before the startup timeout.")
