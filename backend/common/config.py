"""Shared configuration for server and desktop."""
import os
import sys
from enum import Enum
from pathlib import Path
from urllib.parse import urlparse

from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.common.version import APP_VERSION

DEFAULT_DATA_DIR = Path("./data")


class AppMode(str, Enum):
    SERVER = "SERVER"
    DESKTOP = "DESKTOP"


class AuthMode(str, Enum):
    SHARED = "shared"
    TRUSTED_LAN = "shared"
    INTERACTIVE = "interactive"


class Settings(BaseSettings):
    # Core
    APP_MODE: AppMode = AppMode.SERVER
    SECRET_KEY: str | None = None
    ALGORITHM: str = "HS256"
    SERVER_HOST: str = "127.0.0.1"
    SERVER_PORT: int = 8000
    SERVER_WORKERS: int = 1
    CORS_ALLOWED_ORIGINS: str = "http://localhost:5173"
    TRUSTED_LAN_MODE: bool = True  # deprecated fallback for older env files
    AUTH_MODE: str | None = None
    TRUSTED_LAN_USER_EMAIL: str = "local@lan"
    TRUSTED_LAN_USER_NAME: str = "Trusted LAN User"
    AUTH_SESSION_EXPIRE_MINUTES: int = 720
    ENTERPRISE_SERVER_URL: str = ""
    APP_VERSION: str = APP_VERSION

    # AI / External Services
    LLM_PROVIDER: str | None = "ollama"
    OPENAI_API_BASE: str = ""
    OPENAI_MODEL_NAME: str = "mistral:latest"
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    SERPER_API_KEY: str = ""  # Optional
    ALLOW_SERVER_DDG_FALLBACK: bool = False
    ENGINE_ENABLED: bool = False
    ENGINE_BASE_URL: str = ""
    ENGINE_API_KEY: str = ""
    ENGINE_MODEL_NAME: str = ""
    ENGINE_TIMEOUT_SECONDS: int = 30
    ENGINE_MAX_RETRIES: int = 2

    # Data Storage
    DATA_DIR: Path = DEFAULT_DATA_DIR
    DATABASE_URL: str = ""
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 5
    DB_POOL_TIMEOUT_SECONDS: int = 30
    DB_POOL_RECYCLE_SECONDS: int = 1800
    QDRANT_URL: str = ""
    QDRANT_API_KEY: str = ""
    QDRANT_MODE: str = "external"
    BUNDLED_QDRANT_BINARY: str = ""
    BUNDLED_QDRANT_CONFIG_PATH: str = ""
    BUNDLED_QDRANT_STORAGE_DIR: str = ""
    BUNDLED_QDRANT_STARTUP_TIMEOUT_SECONDS: int = 30
    QDRANT_TIMEOUT_SECONDS: int = 30
    QDRANT_PREFER_GRPC: bool = False
    INGESTION_CONCURRENCY: int = 2

    # Desktop Data Collection
    DATA_COLLECTION_ENABLED: bool = False
    CLIPBOARD_COLLECTION_ENABLED: bool = False
    CLIPBOARD_STORE_RAW_TEXT: bool = False
    CLIPBOARD_MAX_CHARS: int = 50000
    FOLDER_WATCH_ENABLED: bool = False
    MIN_CLIPBOARD_CHARS: int = 20
    DOC_MAX_MB: int = 10
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 200
    FOLDER_UPLOAD_ENABLED: bool = True
    FOLDER_UPLOAD_DIR: str = "uploads/folders"
    FOLDER_UPLOAD_DELETE_ON_RESTART: bool = True
    FOLDER_UPLOAD_MAX_ARCHIVE_MB: int = 250
    FOLDER_UPLOAD_MAX_EXPANDED_MB: int = 1000
    FOLDER_UPLOAD_MAX_FILES: int = 500
    QDRANT_COLLECTION_USER_DOCS: str = "user_documents"
    QDRANT_COLLECTION_SESSION_MEMORY: str = "session_memory"
    QDRANT_COLLECTION_USER_PROFILE: str = "user_profile"
    RETENTION_DAYS_EVENTS_RAW: int = 14
    EVENT_QUEUE_MAX: int = 500
    DEDUPE_WINDOW_SECONDS: int = 120
    PROFILE_ROLLUP_EVERY: int = 5

    model_config = SettingsConfigDict(env_file=str(Path(__file__).resolve().parents[2] / ".env"), extra="ignore")

    def cors_origins(self) -> list[str]:
        origins = [origin.strip() for origin in self.CORS_ALLOWED_ORIGINS.split(",") if origin.strip()]
        return origins or ["http://localhost:5173"]

    def auth_mode(self) -> AuthMode:
        if self.APP_MODE == AppMode.DESKTOP:
            return AuthMode.SHARED
        configured = (self.AUTH_MODE or "").strip().lower()
        if configured in {"shared", "trusted_lan"}:
            return AuthMode.SHARED
        if configured == AuthMode.INTERACTIVE.value:
            return AuthMode.INTERACTIVE
        return AuthMode.SHARED if self.TRUSTED_LAN_MODE else AuthMode.INTERACTIVE

    def is_trusted_lan_auth(self) -> bool:
        return self.auth_mode() == AuthMode.TRUSTED_LAN

    def database_url(self) -> str:
        if self.APP_MODE == AppMode.DESKTOP:
            return f"sqlite:///{self.DATA_DIR / 'lumeward.db'}"
        configured = self.DATABASE_URL.strip()
        if configured:
            return configured
        raise RuntimeError("Server mode requires DATABASE_URL using PostgreSQL.")

    def validate_storage_configuration(self) -> None:
        if self.APP_MODE == AppMode.DESKTOP:
            return
        database_url = self.DATABASE_URL.strip().lower()
        if not database_url.startswith(("postgresql://", "postgresql+psycopg://")):
            raise RuntimeError("Server mode requires DATABASE_URL using PostgreSQL.")
        if self.QDRANT_MODE not in {"external", "bundled"}:
            raise RuntimeError("QDRANT_MODE must be external or bundled.")
        if not self.QDRANT_URL.strip():
            raise RuntimeError("Server mode requires QDRANT_URL; embedded Qdrant is desktop-only.")
        if self.SERVER_WORKERS < 1:
            raise RuntimeError("SERVER_WORKERS must be at least 1.")
        if self.DB_POOL_SIZE < 1 or self.DB_MAX_OVERFLOW < 0:
            raise RuntimeError("Database pool settings are invalid.")
        if self.DB_POOL_TIMEOUT_SECONDS < 1 or self.DB_POOL_RECYCLE_SECONDS < 1:
            raise RuntimeError("Database pool timeouts must be positive.")
        if self.QDRANT_TIMEOUT_SECONDS < 1:
            raise RuntimeError("QDRANT_TIMEOUT_SECONDS must be positive.")
        if self.BUNDLED_QDRANT_STARTUP_TIMEOUT_SECONDS < 1:
            raise RuntimeError("BUNDLED_QDRANT_STARTUP_TIMEOUT_SECONDS must be positive.")
        if self.INGESTION_CONCURRENCY < 1:
            raise RuntimeError("INGESTION_CONCURRENCY must be at least 1.")
        qdrant_url = urlparse(self.QDRANT_URL.strip())
        if qdrant_url.scheme not in {"http", "https"} or not qdrant_url.netloc:
            raise RuntimeError("QDRANT_URL must be an absolute http:// or https:// URL.")

    def engine_model_name(self) -> str:
        return self.ENGINE_MODEL_NAME.strip() or self.OPENAI_MODEL_NAME

    def engine_base_url(self) -> str:
        return self.ENGINE_BASE_URL.strip().rstrip("/")

    def apply_runtime_overrides(
        self,
        *,
        app_mode: AppMode | None = None,
        auth_mode: AuthMode | None = None,
        server_host: str | None = None,
        server_port: int | None = None,
    ) -> None:
        if app_mode is not None:
            self.APP_MODE = app_mode
        if auth_mode is not None:
            self.AUTH_MODE = auth_mode
        if server_host is not None:
            self.SERVER_HOST = server_host
        if server_port is not None:
            self.SERVER_PORT = server_port

    def _desktop_data_dir(self) -> Path:
        if sys.platform == "win32":
            appdata = os.environ.get("APPDATA")
            if appdata:
                return Path(appdata) / "Lumeward"
            return Path.home() / "AppData" / "Roaming" / "Lumeward"
        if sys.platform == "darwin":
            return Path.home() / "Library" / "Application Support" / "Lumeward"
        xdg_data_home = os.environ.get("XDG_DATA_HOME")
        if xdg_data_home:
            return Path(xdg_data_home) / "Lumeward"
        return Path.home() / ".local" / "share" / "Lumeward"

    def configure(self) -> None:
        """Set DATA_DIR based on APP_MODE and ensure it exists."""
        data_dir_override = os.environ.get("DATA_DIR")
        if data_dir_override:
            base_dir = Path(data_dir_override)
        elif self.APP_MODE == AppMode.DESKTOP:
            base_dir = self._desktop_data_dir()
        else:
            base_dir = DEFAULT_DATA_DIR

        self.DATA_DIR = base_dir

        self.DATA_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.configure()
