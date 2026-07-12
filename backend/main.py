import argparse
import logging
import os
import sys
from pathlib import Path

# Add project root to sys.path to allow imports from 'backend'
sys.path.append(str(Path(__file__).resolve().parent.parent))

from backend.common.config import AppMode, AuthMode, settings
from backend.common.logging import configure_logging
from backend.common.services.llm.provider_factory import check_remote_engine_ready


def build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Start Lumeward in server or desktop mode.")
    parser.add_argument("--mode", choices=("desktop", "server"))
    parser.add_argument("--auth-mode", choices=("shared", "trusted_lan", "interactive"))
    parser.add_argument("--host")
    parser.add_argument("--port", type=int)
    parser.add_argument("--reload", action="store_true")
    return parser


def apply_cli_overrides(args: argparse.Namespace) -> tuple[AppMode, bool]:
    app_mode = AppMode(args.mode.upper()) if args.mode else settings.APP_MODE
    auth_mode = AuthMode.INTERACTIVE if args.auth_mode == "interactive" else (
        AuthMode.SHARED if args.auth_mode in {"shared", "trusted_lan"} else None
    )

    if app_mode == AppMode.DESKTOP and (args.host or args.port or args.reload):
        raise ValueError("--host, --port, and --reload are only valid in server mode.")
    if app_mode == AppMode.DESKTOP and auth_mode == AuthMode.INTERACTIVE:
        raise ValueError("Interactive auth is not valid in desktop mode.")

    settings.apply_runtime_overrides(
        app_mode=app_mode,
        auth_mode=auth_mode,
        server_host=args.host,
        server_port=args.port,
    )
    os.environ["APP_MODE"] = app_mode.value
    if auth_mode is not None:
        os.environ["AUTH_MODE"] = auth_mode.value
    settings.configure()
    return app_mode, args.reload


def start_server(*, reload: bool = False) -> None:
    logger = logging.getLogger(__name__)
    logger.info("Starting Application as Server...")
    if settings.auth_mode() != AuthMode.TRUSTED_LAN and not settings.SECRET_KEY:
        raise RuntimeError("SECRET_KEY must be set in .env for server mode.")
    settings.validate_storage_configuration()

    try:
        import uvicorn

        if settings.ENGINE_ENABLED:
            check_remote_engine_ready(log_only=True)

        uvicorn_kwargs = {
            "app": "backend.server.app:create_app",
            "factory": True,
            "host": settings.SERVER_HOST,
            "port": settings.SERVER_PORT,
            "reload": reload,
        }
        if not reload:
            uvicorn_kwargs["workers"] = settings.SERVER_WORKERS

        uvicorn.run(**uvicorn_kwargs)

    except ImportError as exc:
        logger.exception("Error starting server: %s", exc)
        logger.error("Ensure 'fastapi', 'uvicorn', 'sqlmodel' are installed.")
        sys.exit(1)


def start_desktop() -> None:
    logger = logging.getLogger(__name__)
    logger.info("Starting Application as Desktop...")
    try:
        if settings.ENGINE_ENABLED:
            check_remote_engine_ready(log_only=True)

        from backend.desktop.main import main as desktop_main

        desktop_main()
    except Exception as exc:
        logger.exception("Error starting desktop app: %s", exc)
        sys.exit(1)


def main(argv: list[str] | None = None) -> int:
    parser = build_cli_parser()
    args = parser.parse_args(argv)
    try:
        app_mode, reload = apply_cli_overrides(args)
    except ValueError as exc:
        parser.error(str(exc))

    configure_logging(app_mode.value)
    if app_mode == AppMode.DESKTOP:
        start_desktop()
    else:
        start_server(reload=reload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
