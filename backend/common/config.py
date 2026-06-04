"""Shared configuration for server and desktop."""
import os
import sys
from enum import Enum
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_DATA_DIR = Path("./data")


class AppMode(str, Enum):
    SERVER = "SERVER"
    DESKTOP = "DESKTOP"


class AuthMode(str, Enum):
    TRUSTED_LAN = "trusted_lan"
    INTERACTIVE = "interactive"


class Settings(BaseSettings):
    # Core
    APP_MODE: AppMode = AppMode.SERVER
    SECRET_KEY: str | None = None
    ALGORITHM: str = "HS256"
    SERVER_HOST: str = "127.0.0.1"
    SERVER_PORT: int = 8000
    CORS_ALLOWED_ORIGINS: str = "http://localhost:5173"
    TRUSTED_LAN_MODE: bool = True
    AUTH_MODE: AuthMode | None = None
    TRUSTED_LAN_USER_EMAIL: str = "local@lan"
    TRUSTED_LAN_USER_NAME: str = "Trusted LAN User"
    AUTH_SESSION_EXPIRE_MINUTES: int = 720

    # AI / External Services
    LLM_PROVIDER: str | None = None
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

    # Desktop Data Collection
    DATA_COLLECTION_ENABLED: bool = True
    CLIPBOARD_COLLECTION_ENABLED: bool = False
    CLIPBOARD_STORE_RAW_TEXT: bool = False
    CLIPBOARD_MAX_CHARS: int = 50000
    FOLDER_WATCH_ENABLED: bool = False
    MIN_CLIPBOARD_CHARS: int = 20
    DOC_MAX_MB: int = 10
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 200
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
            return AuthMode.TRUSTED_LAN
        if self.AUTH_MODE is not None:
            return self.AUTH_MODE
        return AuthMode.TRUSTED_LAN if self.TRUSTED_LAN_MODE else AuthMode.INTERACTIVE

    def is_trusted_lan_auth(self) -> bool:
        return self.auth_mode() == AuthMode.TRUSTED_LAN

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
