from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from backend.common.services.telemetry.consent import add_folder_consent
from backend.desktop.preferences import (
    apply_llm_preferences_to_settings,
    get_clipboard_collection_enabled,
    get_clipboard_store_raw_text_enabled,
    get_data_collection_enabled,
    get_llm_base_url,
    get_llm_model_name,
    get_llm_provider,
    get_theme_mode,
    set_clipboard_collection_enabled,
    set_clipboard_store_raw_text_enabled,
    set_data_collection_enabled,
    set_llm_base_url,
    set_llm_model_name,
    set_llm_provider,
    set_theme_mode,
)
from backend.desktop.security import delete_secret, get_secret, set_secret


class SettingsDialog(QDialog):
    def __init__(self, parent=None, on_saved=None):
        super().__init__(parent)
        self._on_saved = on_saved
        self.setWindowTitle("Settings")
        self.resize(480, 420)

        layout = QVBoxLayout(self)

        appearance_group = QGroupBox("Appearance")
        appearance_layout = QFormLayout(appearance_group)
        self.theme_mode_input = QComboBox()
        self.theme_mode_input.addItem("System Default", "system")
        self.theme_mode_input.addItem("Dark", "dark")
        self.theme_mode_input.addItem("Light", "light")
        saved_theme_mode = get_theme_mode()
        index = max(self.theme_mode_input.findData(saved_theme_mode), 0)
        self.theme_mode_input.setCurrentIndex(index)
        appearance_layout.addRow("Theme", self.theme_mode_input)
        layout.addWidget(appearance_group)

        llm_group = QGroupBox("LLM")
        llm_layout = QFormLayout(llm_group)
        self.provider_input = QComboBox()
        self.provider_input.addItem("Ollama (local)", "ollama")
        self.provider_input.addItem("OpenAI compatible", "openai")
        self.provider_input.addItem("Google Gemini", "google")
        provider_index = max(self.provider_input.findData(get_llm_provider()), 0)
        self.provider_input.setCurrentIndex(provider_index)
        llm_layout.addRow("Provider", self.provider_input)

        self.base_url_input = QLineEdit()
        self.base_url_input.setText(get_llm_base_url())
        llm_layout.addRow("Base URL", self.base_url_input)

        self.model_input = QLineEdit()
        self.model_input.setText(get_llm_model_name())
        llm_layout.addRow("Model", self.model_input)
        layout.addWidget(llm_group)

        api_group = QGroupBox("API Keys")
        api_layout = QVBoxLayout(api_group)
        api_layout.addWidget(QLabel("OpenAI API Key (Optional):"))
        self.openai_input = QLineEdit()
        self.openai_input.setEchoMode(QLineEdit.Password)
        self.openai_input.setText(get_secret("openai_api_key") or "")
        api_layout.addWidget(self.openai_input)

        api_layout.addWidget(QLabel("Google Gemini API Key (Optional):"))
        self.gemini_input = QLineEdit()
        self.gemini_input.setEchoMode(QLineEdit.Password)
        self.gemini_input.setText(get_secret("gemini_api_key") or "")
        api_layout.addWidget(self.gemini_input)

        api_layout.addWidget(QLabel("Serper API Key (For Web Search):"))
        self.serper_input = QLineEdit()
        self.serper_input.setEchoMode(QLineEdit.Password)
        self.serper_input.setText(get_secret("serper_api_key") or "")
        api_layout.addWidget(self.serper_input)
        layout.addWidget(api_group)

        ingestion_group = QGroupBox("Ingestion")
        ingestion_layout = QVBoxLayout(ingestion_group)
        ingestion_layout.addWidget(QLabel("Watched Folders (opt-in for ingestion):"))
        self.add_folder_btn = QPushButton("Add Folder to Watch")
        self.add_folder_btn.clicked.connect(self.add_folder)
        ingestion_layout.addWidget(self.add_folder_btn)
        layout.addWidget(ingestion_group)

        privacy_group = QGroupBox("Privacy")
        privacy_layout = QVBoxLayout(privacy_group)

        self.data_collection_checkbox = QCheckBox("Enable desktop telemetry data collection")
        self.data_collection_checkbox.setChecked(get_data_collection_enabled())
        self.data_collection_checkbox.toggled.connect(self._on_data_collection_toggled)
        privacy_layout.addWidget(self.data_collection_checkbox)

        self.clipboard_collection_checkbox = QCheckBox("Enable clipboard collection (opt-in)")
        self.clipboard_collection_checkbox.setChecked(get_clipboard_collection_enabled())
        self.clipboard_collection_checkbox.toggled.connect(self._on_clipboard_collection_toggled)
        privacy_layout.addWidget(self.clipboard_collection_checkbox)

        self.clipboard_raw_checkbox = QCheckBox("Store raw clipboard text (higher sensitivity)")
        self.clipboard_raw_checkbox.setChecked(get_clipboard_store_raw_text_enabled())
        privacy_layout.addWidget(self.clipboard_raw_checkbox)
        layout.addWidget(privacy_group)
        self._on_data_collection_toggled(self.data_collection_checkbox.isChecked())

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save_settings)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def save_settings(self) -> None:
        openai_key = self.openai_input.text().strip()
        gemini_key = self.gemini_input.text().strip()
        serper_key = self.serper_input.text().strip()
        theme_mode = str(self.theme_mode_input.currentData())
        provider = str(self.provider_input.currentData())
        base_url = self.base_url_input.text().strip()
        model_name = self.model_input.text().strip()

        set_llm_provider(provider)
        set_llm_base_url(base_url)
        set_llm_model_name(model_name)
        apply_llm_preferences_to_settings()
        if openai_key:
            set_secret("openai_api_key", openai_key)
        else:
            delete_secret("openai_api_key")
        if gemini_key:
            set_secret("gemini_api_key", gemini_key)
        else:
            delete_secret("gemini_api_key")
        if serper_key:
            set_secret("serper_api_key", serper_key)
        else:
            delete_secret("serper_api_key")

        set_data_collection_enabled(self.data_collection_checkbox.isChecked())
        set_clipboard_collection_enabled(self.clipboard_collection_checkbox.isChecked())
        set_clipboard_store_raw_text_enabled(
            self.clipboard_collection_checkbox.isChecked() and self.clipboard_raw_checkbox.isChecked()
        )
        set_theme_mode(theme_mode)

        if self._on_saved is not None:
            self._on_saved()

        QMessageBox.information(self, "Settings", "Settings saved.")
        self.accept()

    def add_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Folder to Watch")
        if not folder:
            return
        add_folder_consent(Path(folder))
        QMessageBox.information(self, "Settings", "Folder consent saved.")

    def _on_data_collection_toggled(self, enabled: bool) -> None:
        self.clipboard_collection_checkbox.setEnabled(enabled)
        if not enabled:
            self.clipboard_collection_checkbox.setChecked(False)
            self.clipboard_raw_checkbox.setChecked(False)
        self._on_clipboard_collection_toggled(enabled and self.clipboard_collection_checkbox.isChecked())

    def _on_clipboard_collection_toggled(self, enabled: bool) -> None:
        self.clipboard_raw_checkbox.setEnabled(enabled and self.data_collection_checkbox.isChecked())
        if not enabled:
            self.clipboard_raw_checkbox.setChecked(False)
