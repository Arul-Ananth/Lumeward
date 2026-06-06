import logging
import queue as std_queue
import time
from datetime import datetime

from PySide6.QtCore import QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QFileDialog, QMainWindow, QToolBar

from backend.common.config import settings
from backend.common.services.llm.tool_policy import describe_search_mode, resolve_search_mode
from backend.desktop.preferences import get_theme_mode
from backend.desktop.security import get_secret
from backend.desktop.services.ai_worker import AIWorker
from backend.desktop.services.ocr_worker import OCRWorker
from backend.desktop.telemetry_manager import TelemetryManager
from backend.desktop.theme import apply_app_theme
from backend.desktop.ui.digest_renderer import render_digest_html
from backend.desktop.ui.global_hotkey import GlobalHotkeyManager
from backend.desktop.ui.main_window_view import PRESET_GUIDANCE, build_main_window_content
from backend.desktop.ui.ollama_dialogs import confirm_ollama_ready
from backend.desktop.ui.overlay import ScreenSnipperOverlay
from backend.desktop.ui.settings_dialog import SettingsDialog
from backend.desktop.ui.signal_bus import get_signal_bus
from backend.desktop.workers.feed_deep_dive_worker import FeedDeepDiveWorker
from backend.desktop.workers.feed_processor_worker import FeedProcessorWorker
from backend.desktop.workers.feed_refresh_worker import FeedDismissWorker, FeedRefreshWorker

logger = logging.getLogger(__name__)
TIME_SENSITIVE_TERMS = ("today", "todays", "today's", "current", "latest", "recent")


class MainWindow(QMainWindow):
    def __init__(
        self,
        user_id: int,
        session_id: str,
        ingestion_queue=None,
        status_queue=None,
        api_process=None,
        api_stop_event=None,
        bridge_token: str | None = None,
        bridge_warning: str | None = None,
    ) -> None:
        super().__init__()
        self.user_id = user_id
        self.session_id = session_id
        self._ingestion_queue = ingestion_queue
        self._status_queue = status_queue
        self._api_process = api_process
        self._api_stop_event = api_stop_event
        self._bridge_token = bridge_token
        self._bridge_started = False
        self._bridge_disabled = False
        self._bridge_deadline = None
        self._ipc_timer: QTimer | None = None

        self._ai_worker: AIWorker | None = None
        self._ocr_worker: OCRWorker | None = None
        self._feed_refresh_worker: FeedRefreshWorker | None = None
        self._feed_processor_worker: FeedProcessorWorker | None = None
        self._feed_dismiss_worker: FeedDismissWorker | None = None
        self._feed_deep_dive_worker: FeedDeepDiveWorker | None = None
        self._context_fragments: list[str] = []
        self._has_result = False
        self._generation_error_pending = False
        self._ollama_checked = False
        self._current_markdown = ""

        self.setWindowTitle("Lumeward")
        self.resize(980, 780)
        self.setAcceptDrops(True)
        self.statusBar()

        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)

        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.open_settings)
        toolbar.addAction(settings_action)

        self.ui = build_main_window_content()
        self.setCentralWidget(self.ui.central_widget)
        self.topic_input = self.ui.topic_input
        self.context_input = self.ui.guidance_input
        self.output_area = self.ui.output_area
        self.generate_btn = self.ui.generate_btn
        self.generate_btn.clicked.connect(self.start_generation)
        self.ui.regenerate_btn.clicked.connect(self.start_generation)
        self.ui.copy_btn.clicked.connect(self.copy_result)
        self.ui.clear_btn.clicked.connect(self.clear_result)
        self.ui.save_btn.clicked.connect(self.save_result_as_markdown)
        self.ui.feed_panel.dismiss_requested.connect(self.dismiss_feed_card)
        self.ui.feed_panel.deep_dive_requested.connect(self.start_feed_deep_dive)
        self.topic_input.textChanged.connect(self._update_action_states)

        for label, button in self.ui.preset_buttons.items():
            preset_text = PRESET_GUIDANCE[label]
            button.clicked.connect(lambda _checked=False, text=preset_text: self._apply_guidance_preset(text))

        self.signal_bus = get_signal_bus()
        self.signal_bus.status_message.connect(self.show_status)
        self.signal_bus.log_message.connect(self.log_message)
        self.signal_bus.progress_update.connect(self.on_ai_progress)
        self.signal_bus.result_ready.connect(self.on_ai_result)
        self.signal_bus.ingest_received.connect(self.on_ingest_payload)
        self.signal_bus.ocr_requested.connect(self.start_ocr)
        self.signal_bus.ocr_result.connect(self.on_ocr_result)
        self.signal_bus.ocr_error.connect(self.on_ocr_error)
        self.signal_bus.snip_requested.connect(self.activate_snipper)

        self.overlay = ScreenSnipperOverlay(self.signal_bus)
        self.hotkey_manager = GlobalHotkeyManager(self.signal_bus)
        self.hotkey_manager.register()

        self.telemetry = TelemetryManager(user_id=user_id, session_id=session_id, output=self.output_area)
        QTimer.singleShot(0, self.telemetry.start)

        if self._api_process is not None:
            self._bridge_deadline = time.monotonic() + 5.0

        if self._ingestion_queue is not None or self._status_queue is not None or self._api_process is not None:
            self._ipc_timer = QTimer(self)
            self._ipc_timer.setInterval(200)
            self._ipc_timer.timeout.connect(self._poll_ipc)
            self._ipc_timer.start()

        self._feed_timer = QTimer(self)
        self._feed_timer.setInterval(60000)
        self._feed_timer.timeout.connect(self.process_feed_events)
        self._feed_timer.start()

        if bridge_warning:
            self.signal_bus.log_message.emit(bridge_warning)
            self.signal_bus.status_message.emit("Browser bridge disabled for this session.")

        self._update_runtime_summary()
        self._update_result_metadata(None)
        self._update_action_states()
        QTimer.singleShot(0, self.process_feed_events)
        QTimer.singleShot(200, self.refresh_feed)

    def open_settings(self) -> None:
        dlg = SettingsDialog(self, on_saved=self._on_settings_saved, bridge_status=self._bridge_status_text())
        dlg.exec()

    def start_generation(self) -> None:
        topic = self.topic_input.text().strip()
        context = self._compose_context()

        if not topic:
            self.show_status("Enter a topic.")
            return

        if self._ai_worker and self._ai_worker.isRunning():
            self.show_status("Generation already running.")
            return

        if not self._confirm_ollama_ready():
            return

        self.telemetry.flush_output_time()
        self.telemetry.emit_generation(topic, context)

        self.show_status("Researching...")
        self._append_activity(f"Starting brief generation for: {topic}")
        self.output_area.clear()
        self._current_markdown = ""
        self._has_result = False
        self._generation_error_pending = False
        self._set_result_placeholder(f"Starting research on '{topic}'... This may take a minute.")

        api_keys = self._current_api_keys()
        search_mode = resolve_search_mode(api_keys=api_keys)
        self._update_runtime_summary(search_mode=search_mode)
        self.signal_bus.log_message.emit(describe_search_mode(api_keys=api_keys))
        self._update_result_metadata(
            topic,
            search_mode=search_mode,
            state="Running",
            grounded=self._is_current_date_grounded(topic),
        )

        self._ai_worker = AIWorker(topic, context, self.user_id, self.session_id, api_keys)
        self._ai_worker.progress_update.connect(self.signal_bus.progress_update)
        self._ai_worker.status_message.connect(self.signal_bus.status_message)
        self._ai_worker.result_ready.connect(self.signal_bus.result_ready)
        self._ai_worker.error_message.connect(self.on_ai_error)
        self._ai_worker.finished.connect(self.on_ai_finished)
        self._ai_worker.start()
        self._update_action_states()

    def start_ocr(self, image) -> None:
        if self._ocr_worker and self._ocr_worker.isRunning():
            self.show_status("OCR already running.")
            return
        self._ocr_worker = OCRWorker(image)
        self._ocr_worker.status_message.connect(self.signal_bus.status_message)
        self._ocr_worker.result_ready.connect(self.signal_bus.ocr_result)
        self._ocr_worker.error_message.connect(self.signal_bus.ocr_error)
        self._ocr_worker.start()
        self._append_activity("OCR started.")

    def show_status(self, message: str) -> None:
        self.statusBar().showMessage(message, 5000)
        self.ui.status_label.setText(message)

    def log_message(self, message: str) -> None:
        self._append_activity(message)

    def on_ai_progress(self, progress: int) -> None:
        self.show_status(f"Progress: {progress}%")

    def on_ai_result(self, result: str) -> None:
        if result:
            self._current_markdown = result
            self.output_area.setHtml(render_digest_html(result, self._current_theme_mode()))
            self.telemetry.mark_output_start()
            topic = self.topic_input.text().strip()
            search_mode = resolve_search_mode(api_keys=self._current_api_keys())
            self._update_result_metadata(
                topic,
                search_mode=search_mode,
                state="Completed",
                grounded=self._is_current_date_grounded(topic),
            )
            self._has_result = True
            self._generation_error_pending = False
            self.show_status("Result ready.")
        else:
            if self._generation_error_pending:
                self._update_action_states()
                return
            self._has_result = False
            self._current_markdown = ""
            self._set_result_placeholder("No output generated.")
            self._update_result_metadata(
                self.topic_input.text().strip(),
                search_mode=resolve_search_mode(api_keys=self._current_api_keys()),
                state="No result",
                grounded=self._is_current_date_grounded(self.topic_input.text().strip()),
            )
        self._update_action_states()

    def on_ai_error(self, message: str) -> None:
        topic = self.topic_input.text().strip()
        search_mode = resolve_search_mode(api_keys=self._current_api_keys())
        self._has_result = False
        self._current_markdown = ""
        self._generation_error_pending = True
        self._set_result_placeholder(message)
        self._append_activity(message)
        self._update_result_metadata(
            topic,
            search_mode=search_mode,
            state="Error",
            grounded=self._is_current_date_grounded(topic),
        )
        self._update_action_states()

    def process_feed_events(self) -> None:
        if self._feed_processor_worker and self._feed_processor_worker.isRunning():
            return
        self._feed_processor_worker = FeedProcessorWorker(self.user_id, self)
        self._feed_processor_worker.processed.connect(self._on_feed_processed)
        self._feed_processor_worker.error_message.connect(self.show_status)
        self._feed_processor_worker.start()

    def refresh_feed(self) -> None:
        if self._feed_refresh_worker and self._feed_refresh_worker.isRunning():
            return
        self._feed_refresh_worker = FeedRefreshWorker(self.user_id, self)
        self._feed_refresh_worker.cards_ready.connect(self.ui.feed_panel.set_cards)
        self._feed_refresh_worker.error_message.connect(self.show_status)
        self._feed_refresh_worker.start()

    def dismiss_feed_card(self, feed_id: int) -> None:
        if self._feed_dismiss_worker and self._feed_dismiss_worker.isRunning():
            return
        self._feed_dismiss_worker = FeedDismissWorker(self.user_id, feed_id, self)
        self._feed_dismiss_worker.completed.connect(lambda _feed_id: self.refresh_feed())
        self._feed_dismiss_worker.error_message.connect(self.show_status)
        self._feed_dismiss_worker.start()

    def start_feed_deep_dive(self, feed_id: int) -> None:
        if self._feed_deep_dive_worker and self._feed_deep_dive_worker.isRunning():
            self.show_status("Deep Dive already running.")
            return
        if not self._confirm_ollama_ready():
            return
        self.ui.feed_panel.set_card_loading(feed_id, True)
        self.show_status("Running Deep Dive...")
        self._feed_deep_dive_worker = FeedDeepDiveWorker(
            self.user_id,
            feed_id,
            self.session_id,
            self._current_api_keys(),
            self,
        )
        self._feed_deep_dive_worker.result_ready.connect(self._on_feed_deep_dive_result)
        self._feed_deep_dive_worker.error_message.connect(self._on_feed_deep_dive_error)
        self._feed_deep_dive_worker.start()

    def _on_feed_processed(self, created: int) -> None:
        if created:
            self.refresh_feed()

    def _on_feed_deep_dive_result(self, feed_id: int, markdown: str) -> None:
        self.ui.feed_panel.set_card_loading(feed_id, False)
        self._current_markdown = markdown
        self.output_area.setHtml(render_digest_html(markdown, self._current_theme_mode()))
        self._has_result = True
        self._generation_error_pending = False
        self.show_status("Deep Dive ready.")
        self.refresh_feed()
        self._update_action_states()

    def _on_feed_deep_dive_error(self, feed_id: int, message: str) -> None:
        self.ui.feed_panel.set_card_loading(feed_id, False)
        self._set_result_placeholder(message)
        self.show_status("Deep Dive failed.")
        self._append_activity(message)
        self._update_action_states()

    def on_ai_finished(self) -> None:
        if not self.output_area.toPlainText().strip():
            self.show_status("Ready.")
        self._update_action_states()

    def on_ocr_result(self, text: str) -> None:
        if text:
            self._append_activity("OCR text attached.")
            self._append_context("Screen OCR", text)
        else:
            self._append_activity("OCR completed with no text detected.")

    def on_ocr_error(self, message: str) -> None:
        self._append_activity(message)

    def on_ingest_payload(self, payload: dict) -> None:
        url = payload.get("url") or ""
        text = payload.get("text") or ""
        if url:
            self._append_activity(f"Ingestion received: {url}")
            self._append_context("Bridge URL", url)
        if text:
            preview = text[:200] + ("..." if len(text) > 200 else "")
            self._append_activity(f"Ingested text preview: {preview}")
            self._append_context("Bridge Text", text)

    def activate_snipper(self) -> None:
        self.overlay.activate()

    def _poll_ipc(self) -> None:
        self._drain_ingestion_queue()
        self._drain_status_queue()
        self._check_bridge_health()

    def _drain_ingestion_queue(self) -> None:
        if self._ingestion_queue is None:
            return
        while True:
            try:
                payload = self._ingestion_queue.get_nowait()
            except std_queue.Empty:
                break
            self.signal_bus.ingest_received.emit(payload)

    def _drain_status_queue(self) -> None:
        if self._status_queue is None:
            return
        while True:
            try:
                message = self._status_queue.get_nowait()
            except std_queue.Empty:
                break
            status = message.get("status")
            port = message.get("port")
            if status == "starting":
                if port:
                    self.show_status(f"Bridge starting on port {port}...")
                else:
                    self.show_status("Bridge starting...")
            elif status == "started":
                self._bridge_started = True
                if port:
                    self.signal_bus.log_message.emit(f"Browser bridge started on port {port}.")
                    self.show_status(f"Bridge ready on port {port}.")
                else:
                    self.signal_bus.log_message.emit("Browser bridge started.")
                    self.show_status("Bridge ready.")
            elif status == "failed":
                error = message.get("error") or "Bridge failed."
                self._disable_bridge(error)
            self._update_runtime_summary()

    def _check_bridge_health(self) -> None:
        if self._bridge_disabled:
            return
        if self._api_process is not None and not self._api_process.is_alive():
            if not self._bridge_started:
                self._disable_bridge("Bridge failed to start.")
            else:
                self._disable_bridge("Bridge stopped unexpectedly.")
            return

        if self._bridge_deadline and not self._bridge_started:
            if time.monotonic() > self._bridge_deadline:
                self._disable_bridge("Bridge unreachable.")

    def _disable_bridge(self, reason: str) -> None:
        if self._bridge_disabled:
            return
        self._bridge_disabled = True
        self.signal_bus.log_message.emit(f"Browser bridge disabled: {reason}")
        self.signal_bus.status_message.emit("Browser bridge disabled.")
        if self._api_stop_event is not None:
            self._api_stop_event.set()
        self._update_runtime_summary()

    def _append_context(self, label: str, content: str) -> None:
        content = content.strip()
        if not content:
            return
        block = f"[{label}]\n{content}"
        if block in self._context_fragments:
            return
        self._context_fragments.append(block)
        self.ui.attached_context_area.setPlainText("\n\n".join(self._context_fragments))
        self._append_activity(f"Attached context added from {label}.")

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:
        if not event.mimeData().hasUrls():
            return
        paths = [url.toLocalFile() for url in event.mimeData().urls()]
        self.telemetry.handle_file_drop(paths)

    def closeEvent(self, event) -> None:
        self.telemetry.flush_output_time()
        self.telemetry.emit_session_end()
        self.telemetry.shutdown()

        self.hotkey_manager.unregister()
        if self._ipc_timer is not None:
            self._ipc_timer.stop()
        if hasattr(self, "_feed_timer"):
            self._feed_timer.stop()

        if self._ocr_worker and self._ocr_worker.isRunning():
            self._ocr_worker.cancel()
            self._ocr_worker.wait(2000)
        if self._ai_worker and self._ai_worker.isRunning():
            self._ai_worker.cancel()
            self._ai_worker.wait(2000)
        for worker in (
            self._feed_refresh_worker,
            self._feed_processor_worker,
            self._feed_dismiss_worker,
            self._feed_deep_dive_worker,
        ):
            if worker and worker.isRunning():
                worker.wait(2000)

        if self._api_stop_event is not None:
            self._api_stop_event.set()
        if self._api_process is not None:
            self._api_process.join(timeout=3)
            if self._api_process.is_alive():
                self._api_process.terminate()
                self._api_process.join(timeout=1)

        super().closeEvent(event)

    def copy_result(self) -> None:
        markdown = self._current_output_markdown().strip()
        if not markdown:
            self.show_status("No result to copy.")
            return
        QApplication.clipboard().setText(markdown)
        self._append_activity("Result copied to clipboard.")

    def clear_result(self) -> None:
        self.output_area.clear()
        self._current_markdown = ""
        self._has_result = False
        self._update_result_metadata(None)
        self._append_activity("Result cleared.")
        self._update_action_states()

    def save_result_as_markdown(self) -> None:
        markdown = self._current_output_markdown().strip()
        if not markdown:
            self.show_status("No result to save.")
            return
        path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Save Brief",
            "lumeward-brief.md",
            "Markdown Files (*.md);;Text Files (*.txt)",
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(markdown)
        self._append_activity(f"Result saved to {path}.")
        self.show_status("Brief saved.")

    def _compose_context(self) -> str:
        parts: list[str] = []
        manual_guidance = self.context_input.toPlainText().strip()
        if manual_guidance:
            parts.append(manual_guidance)
        parts.extend(self._context_fragments)
        return "\n\n".join(parts).strip()

    def _apply_guidance_preset(self, preset_text: str) -> None:
        current = self.context_input.toPlainText().strip()
        if preset_text in current:
            return
        updated = f"{current}\n{preset_text}".strip() if current else preset_text
        self.context_input.setPlainText(updated)
        self._append_activity(f"Guidance preset applied: {preset_text}")

    def _append_activity(self, message: str) -> None:
        self.ui.log_widget.append_message(message)
        logger.info("Desktop activity: %s", message)

    def _current_api_keys(self) -> dict[str, str | None]:
        return {
            "openai_api_key": get_secret("openai_api_key"),
            "gemini_api_key": get_secret("gemini_api_key"),
            "serper_api_key": get_secret("serper_api_key"),
        }

    def _confirm_ollama_ready(self) -> bool:
        if settings.ENGINE_ENABLED or (settings.LLM_PROVIDER or "").strip().lower() != "ollama":
            return True
        if self._ollama_checked:
            return True
        ready = confirm_ollama_ready(
            self,
            append_activity=self._append_activity,
            show_status=self.show_status,
        )
        if ready:
            self._ollama_checked = True
        return ready

    def _update_runtime_summary(self, *, search_mode: str | None = None) -> None:
        resolved_search_mode = search_mode or resolve_search_mode(api_keys=self._current_api_keys())
        search_label = {
            "serper": "Serper",
            "fallback": "Fallback",
            "disabled": "Disabled",
        }.get(resolved_search_mode, resolved_search_mode.title())
        self.ui.capability_label.setText(search_label)

    def _bridge_status_text(self) -> str:
        if self._bridge_disabled:
            return "Disabled for this session."
        if self._api_process is None:
            return "Unavailable in this session."
        if self._bridge_started:
            return "Ready on local loopback. Requests require the runtime bridge token."
        return "Starting on local loopback. Requests require the runtime bridge token."

    def _update_result_metadata(
        self,
        topic: str | None,
        *,
        search_mode: str | None = None,
        state: str = "Idle",
        grounded: bool = False,
    ) -> None:
        if not topic:
            self.ui.result_meta_label.setText("No result")
            return
        search_label = {
            "serper": "Serper",
            "fallback": "Fallback",
            "disabled": "Disabled",
            None: "Unknown",
        }[search_mode] if search_mode in {"serper", "fallback", "disabled"} or search_mode is None else search_mode
        generated_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
        self.ui.result_meta_label.setText(
            f"{state} | {generated_at} | {search_label}"
        )

    def _current_output_markdown(self) -> str:
        return self._current_markdown or self.output_area.toPlainText()

    def _set_result_placeholder(self, message: str) -> None:
        self.output_area.setPlainText(message)

    def _is_current_date_grounded(self, topic: str) -> bool:
        lowered = topic.lower()
        return any(term in lowered for term in TIME_SENSITIVE_TERMS)

    def _on_settings_saved(self) -> None:
        self.telemetry.reload_preferences()
        app = QApplication.instance()
        if app is not None:
            apply_app_theme(app, get_theme_mode())
        if self._current_markdown:
            self.output_area.setHtml(render_digest_html(self._current_markdown, self._current_theme_mode()))
        self._append_activity("Settings saved.")
        self._update_runtime_summary()
        self._update_action_states()

    def _update_action_states(self) -> None:
        has_topic = bool(self.topic_input.text().strip())
        has_output = self._has_result and bool(self.output_area.toPlainText().strip())
        running = self._ai_worker is not None and self._ai_worker.isRunning()
        self.generate_btn.setEnabled(has_topic and not running)
        self.ui.regenerate_btn.setEnabled(has_topic and not running)
        self.ui.copy_btn.setEnabled(has_output)
        self.ui.clear_btn.setEnabled(has_output)
        self.ui.save_btn.setEnabled(has_output)

    def _current_theme_mode(self) -> str:
        app = QApplication.instance()
        if app is None:
            return "dark"
        mode = app.property("lumeward.theme_effective")
        return "light" if mode == "light" else "dark"
