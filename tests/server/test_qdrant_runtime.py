from __future__ import annotations

from pathlib import Path

import pytest

from backend.common.config import settings
from backend.common.services.memory import vector_db
from backend.server import qdrant_runtime


def test_bundled_qdrant_configuration_resolves_configured_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    binary = tmp_path / "qdrant.exe"
    config = tmp_path / "production.yaml"
    storage = tmp_path / "storage"
    binary.touch()
    config.touch()

    monkeypatch.setattr(settings, "BUNDLED_QDRANT_BINARY", str(binary))
    monkeypatch.setattr(settings, "BUNDLED_QDRANT_CONFIG_PATH", str(config))
    monkeypatch.setattr(settings, "BUNDLED_QDRANT_STORAGE_DIR", str(storage))

    assert qdrant_runtime.validate_bundled_qdrant_configuration() == (
        binary.resolve(),
        config.resolve(),
        storage.resolve(),
    )


def test_bundled_qdrant_configuration_rejects_missing_binary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(settings, "BUNDLED_QDRANT_BINARY", str(tmp_path / "missing.exe"))

    with pytest.raises(RuntimeError, match="executable was not found"):
        qdrant_runtime.validate_bundled_qdrant_configuration()


def test_qdrant_readiness_wraps_connection_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class UnavailableClient:
        def get_collections(self) -> None:
            raise OSError("connection refused")

    monkeypatch.setattr(vector_db, "get_client", lambda: UnavailableClient())
    monkeypatch.setattr(settings, "QDRANT_URL", "http://127.0.0.1:6333")

    with pytest.raises(vector_db.QdrantUnavailableError, match="QDRANT_MODE=bundled"):
        vector_db.check_qdrant_ready()
