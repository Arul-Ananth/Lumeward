import asyncio
import logging
import multiprocessing
import sys
import uuid
from pathlib import Path

import qasync
from PySide6.QtWidgets import QApplication, QInputDialog, QLineEdit, QMessageBox
from sqlmodel import Session

# Fix path resolution
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from backend.common.config import AppMode, settings
from backend.common.database import create_db_and_tables, get_engine
from backend.common.logging import configure_logging
from backend.common.services.auth.store import ensure_desktop_local_user
from backend.desktop.preferences import apply_llm_preferences_to_settings, get_enterprise_server_url, get_theme_mode
from backend.desktop.services.enterprise_client import EnterpriseClient
from backend.desktop.theme import apply_app_theme, install_system_theme_listener
from backend.desktop.ui.main_window import MainWindow
from backend.desktop.ui.signal_bus import get_signal_bus
from backend.desktop.workers.cron_digest import CronDigestWorker

LOCAL_USER_EMAIL = "local@desktop"
LOCAL_USER_NAME = "Desktop User"

logger = logging.getLogger(__name__)


def ensure_local_user() -> int:
    """Ensure a fixed local user exists for Desktop mode (no auth)."""
    with Session(get_engine()) as session:
        user, _identity = ensure_desktop_local_user(
            session,
            email=LOCAL_USER_EMAIL,
            full_name=LOCAL_USER_NAME,
        )
        return user.id


def main() -> None:
    settings.configure()
    apply_llm_preferences_to_settings()
    configure_logging(settings.APP_MODE.value)

    app = QApplication(sys.argv)
    app.setOrganizationName("Lumeward")
    app.setApplicationName("Lumeward")
    apply_app_theme(app, get_theme_mode())
    install_system_theme_listener(app)

    get_signal_bus()

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    create_db_and_tables()
    user_id = ensure_local_user()
    enterprise_client = None
    enterprise_server_url = get_enterprise_server_url()
    if enterprise_server_url:
        enterprise_client = EnterpriseClient(
            enterprise_server_url,
            connect_timeout=settings.ENTERPRISE_CONNECT_TIMEOUT_SECONDS,
            request_timeout=settings.ENTERPRISE_REQUEST_TIMEOUT_SECONDS,
            generation_timeout=settings.ENTERPRISE_GENERATION_TIMEOUT_SECONDS,
        )
        has_account = QMessageBox.question(
            None,
            "Enterprise sign in",
            "Do you already have an enterprise account?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
        )
        if has_account == QMessageBox.StandardButton.Cancel:
            return
        full_name = ""
        if has_account == QMessageBox.StandardButton.No:
            full_name, ok = QInputDialog.getText(None, "Create enterprise account", "Full name:")
            if not ok or not full_name.strip():
                return
        email, ok = QInputDialog.getText(None, "Enterprise sign in", "Email:")
        if not ok or not email.strip():
            return
        password, ok = QInputDialog.getText(None, "Enterprise sign in", "Password:", QLineEdit.EchoMode.Password)
        if not ok:
            return
        try:
            if has_account == QMessageBox.StandardButton.No:
                enterprise_client.signup(full_name.strip(), email.strip(), password)
            enterprise_client.login(email.strip(), password)
            user_id = enterprise_client.user_id or user_id
        except Exception as exc:
            QMessageBox.critical(None, "Enterprise sign in failed", str(exc))
            return

    cron_worker = None if enterprise_client else CronDigestWorker()
    if cron_worker:
        cron_worker.start()
        app.aboutToQuit.connect(cron_worker.stop)

    session_id = uuid.uuid4().hex
    window = MainWindow(
        user_id=user_id,
        session_id=session_id,
        enterprise_client=enterprise_client,
    )
    window.show()

    with loop:
        loop.run_forever()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    settings.APP_MODE = AppMode.DESKTOP
    main()
