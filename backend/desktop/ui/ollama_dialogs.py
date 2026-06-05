from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QMessageBox, QWidget

from backend.common.config import settings
from backend.desktop.services.ollama_runtime import ping_ollama, start_ollama


def confirm_ollama_ready(
    parent: QWidget,
    *,
    append_activity: Callable[[str], None],
    show_status: Callable[[str], None],
) -> bool:
    response = QMessageBox.question(
        parent,
        "Check Ollama",
        (
            "Lumeward uses Ollama by default for local generation.\n\n"
            f"It can check `{settings.OPENAI_API_BASE or 'http://localhost:11434'}` before generating. "
            "This sends only a local health request and does not send your prompt.\n\n"
            "Check Ollama now?"
        ),
        QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
        QMessageBox.Yes,
    )
    if response == QMessageBox.Cancel:
        return False
    if response == QMessageBox.No:
        return True

    check = ping_ollama(settings.OPENAI_API_BASE)
    if check.ok:
        append_activity(check.message)
        show_status("Ollama is reachable.")
        return True

    start_response = QMessageBox.question(
        parent,
        "Ollama Not Reachable",
        (
            f"{check.message}\n\n"
            "Lumeward can try to run `ollama serve` for this session. "
            "No admin permission is requested.\n\n"
            "Try to start Ollama?"
        ),
        QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
        QMessageBox.Yes,
    )
    if start_response == QMessageBox.Cancel:
        return False
    if start_response == QMessageBox.No:
        return True

    started = start_ollama()
    append_activity(started.message)
    if not started.ok:
        QMessageBox.warning(parent, "Ollama", started.message)
        return True

    retry = ping_ollama(settings.OPENAI_API_BASE, timeout_seconds=5.0)
    append_activity(retry.message)
    if retry.ok:
        show_status("Ollama is reachable.")
        return True

    QMessageBox.warning(
        parent,
        "Ollama",
        f"{retry.message}\n\nGeneration may still fail until Ollama is running and the model is available.",
    )
    return True
