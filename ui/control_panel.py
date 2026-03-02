"""Control panel — device/model/language selectors, start/stop, log area."""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QTextEdit, QGroupBox, QFormLayout, QGridLayout,
    QCheckBox, QMessageBox,
)

from core.audio import list_audio_devices
from core.pipeline import Pipeline
from ui.overlay import SubtitleOverlay
from ui.overlay_settings import OverlaySettingsDialog
from ui.translations import UI_LANGUAGES, t
from settings import load_settings, save_settings
from config import APP_VERSION, WHISPER_MODEL, OLLAMA_MODEL, INPUT_LANGUAGES, TARGET_LANGUAGES, BUFFER_PRESETS


DARK_STYLE = """
QWidget {
    background-color: #18181b;
    color: #e4e4e7;
    font-family: "Segoe UI";
}
QGroupBox {
    border: 1px solid #3f3f46;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 14px;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}
QComboBox, QPushButton {
    background-color: #27272a;
    border: 1px solid #3f3f46;
    border-radius: 4px;
    padding: 6px 10px;
    min-height: 20px;
}
QComboBox:hover, QPushButton:hover {
    border-color: #a1a1aa;
}
QPushButton#startBtn {
    background-color: #16a34a;
    color: white;
    font-weight: bold;
    font-size: 14px;
    padding: 10px;
}
QPushButton#startBtn:hover {
    background-color: #15803d;
}
QPushButton#stopBtn {
    background-color: #dc2626;
    color: white;
    font-weight: bold;
    font-size: 14px;
    padding: 10px;
}
QPushButton#stopBtn:hover {
    background-color: #b91c1c;
}
QTextEdit {
    background-color: #09090b;
    border: 1px solid #3f3f46;
    border-radius: 4px;
    font-family: "Cascadia Code", "Consolas", monospace;
    font-size: 12px;
}
QCheckBox {
    spacing: 6px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 2px solid #71717a;
    border-radius: 3px;
    background: transparent;
}
QCheckBox::indicator:checked {
    background: #facc15;
    border-color: #facc15;
}
QCheckBox::indicator:hover {
    border-color: #a1a1aa;
}
QLabel#statusLabel {
    color: #a1a1aa;
    font-size: 12px;
}
"""


class ControlPanel(QWidget):
    """Main control window for StreamSub."""

    def __init__(self):
        super().__init__()
        self._pipeline = None
        self._overlay = SubtitleOverlay()
        self._lang = "en"
        self._setup_window()
        self._setup_ui()
        self._load_devices()
        self._restore_settings()

    def _setup_window(self):
        self.setWindowTitle(f"StreamSub v{APP_VERSION}")
        self.setMinimumSize(450, 740)
        self.resize(450, 740)
        self.setStyleSheet(DARK_STYLE)

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        # Title
        title = QLabel(f"StreamSub  v{APP_VERSION}")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(title)

        self._subtitle_label = QLabel(t("subtitle", self._lang))
        self._subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._subtitle_label.setStyleSheet("color: #71717a; font-size: 11px;")
        root.addWidget(self._subtitle_label)

        # --- UI Language selector ---
        lang_row = QHBoxLayout()
        self._lbl_ui_lang = QLabel(t("label_ui_lang", self._lang))
        self._lbl_ui_lang.setStyleSheet("color: #a1a1aa; font-size: 11px;")
        lang_row.addStretch()
        lang_row.addWidget(self._lbl_ui_lang)
        self.lang_combo = QComboBox()
        self.lang_combo.setMaximumWidth(120)
        for label, code in UI_LANGUAGES:
            self.lang_combo.addItem(label, code)
        self.lang_combo.currentIndexChanged.connect(self._apply_language)
        lang_row.addWidget(self.lang_combo)
        self._gear_btn = QPushButton("\u2699")
        self._gear_btn.setToolTip(t("btn_overlay_settings", self._lang))
        self._gear_btn.setFixedSize(30, 30)
        self._gear_btn.setStyleSheet(
            "font-size: 16px; padding: 0; min-height: 0;"
        )
        self._gear_btn.clicked.connect(self._open_overlay_settings)
        lang_row.addWidget(self._gear_btn)
        lang_row.addStretch()
        root.addLayout(lang_row)

        # --- Audio group ---
        self._audio_grp = QGroupBox(t("group_audio", self._lang))
        audio_form = QFormLayout(self._audio_grp)
        self.device_combo = QComboBox()
        self._lbl_device = QLabel(t("label_device", self._lang))
        audio_form.addRow(self._lbl_device, self.device_combo)
        self._refresh_btn = QPushButton(t("btn_refresh", self._lang))
        self._refresh_btn.clicked.connect(self._load_devices)
        audio_form.addRow(QLabel(""), self._refresh_btn)

        self.buffer_combo = QComboBox()
        for label, max_s, min_s in BUFFER_PRESETS:
            self.buffer_combo.addItem(label, (max_s, min_s))
        self.buffer_combo.setCurrentIndex(2)  # default: Accurate (8s)
        self._lbl_buffer = QLabel(t("label_buffer", self._lang))
        audio_form.addRow(self._lbl_buffer, self.buffer_combo)

        root.addWidget(self._audio_grp)

        # --- Model group ---
        self._model_grp = QGroupBox(t("group_models", self._lang))
        model_form = QFormLayout(self._model_grp)

        self.whisper_combo = QComboBox()
        self.whisper_combo.addItems(["large-v3-turbo", "large-v3", "medium", "small", "base"])
        self.whisper_combo.setCurrentText(WHISPER_MODEL)
        self._lbl_whisper = QLabel(t("label_whisper", self._lang))
        model_form.addRow(self._lbl_whisper, self.whisper_combo)

        ollama_label = QLabel(OLLAMA_MODEL)
        ollama_label.setStyleSheet("color: #a1a1aa;")
        self._lbl_ollama = QLabel(t("label_ollama", self._lang))
        model_form.addRow(self._lbl_ollama, ollama_label)
        root.addWidget(self._model_grp)

        # --- Input Language ---
        self._input_grp = QGroupBox(t("group_input", self._lang))
        input_form = QFormLayout(self._input_grp)
        self.input_lang_combo = QComboBox()
        for label, code in INPUT_LANGUAGES:
            self.input_lang_combo.addItem(label, code)
        self.input_lang_combo.setCurrentIndex(0)
        self._lbl_source = QLabel(t("label_source", self._lang))
        input_form.addRow(self._lbl_source, self.input_lang_combo)
        root.addWidget(self._input_grp)

        # --- Target Languages (multi-select checkboxes) ---
        self._target_grp = QGroupBox(t("group_target", self._lang))
        target_layout = QGridLayout(self._target_grp)
        target_layout.setSpacing(4)

        self._target_cbs: dict[str, QCheckBox] = {}
        for i, lang in enumerate(TARGET_LANGUAGES):
            cb = QCheckBox(lang)
            row = i // 3
            col = i % 3
            target_layout.addWidget(cb, row, col)
            self._target_cbs[lang] = cb

        # Default: Thai + English checked
        if "Thai" in self._target_cbs:
            self._target_cbs["Thai"].setChecked(True)
        if "English" in self._target_cbs:
            self._target_cbs["English"].setChecked(True)

        root.addWidget(self._target_grp)

        # --- Start / Stop ---
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton(t("btn_start", self._lang))
        self.start_btn.setObjectName("startBtn")
        self.start_btn.clicked.connect(self._on_start)
        btn_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton(t("btn_stop", self._lang))
        self.stop_btn.setObjectName("stopBtn")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._on_stop)
        btn_layout.addWidget(self.stop_btn)
        root.addLayout(btn_layout)

        # --- Status ---
        self.status_label = QLabel(t("status_ready", self._lang))
        self.status_label.setObjectName("statusLabel")
        root.addWidget(self.status_label)

        # --- Log area ---
        self._log_grp = QGroupBox(t("group_log", self._lang))
        log_layout = QVBoxLayout(self._log_grp)
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMinimumHeight(100)
        log_layout.addWidget(self.log_area)
        root.addWidget(self._log_grp, 1)  # stretch factor = 1, expands with window

    # --- Language switching ---

    def _apply_language(self):
        lang = self.lang_combo.currentData()
        if not lang:
            return
        self._lang = lang
        self.setWindowTitle(f"{t('window_title', lang)} v{APP_VERSION}")
        self._subtitle_label.setText(t("subtitle", lang))
        self._lbl_ui_lang.setText(t("label_ui_lang", lang))
        self._audio_grp.setTitle(t("group_audio", lang))
        self._lbl_device.setText(t("label_device", lang))
        self._refresh_btn.setText(t("btn_refresh", lang))
        self._lbl_buffer.setText(t("label_buffer", lang))
        self._model_grp.setTitle(t("group_models", lang))
        self._lbl_whisper.setText(t("label_whisper", lang))
        self._lbl_ollama.setText(t("label_ollama", lang))
        self._input_grp.setTitle(t("group_input", lang))
        self._lbl_source.setText(t("label_source", lang))
        self._target_grp.setTitle(t("group_target", lang))
        self.start_btn.setText(t("btn_start", lang))
        self.stop_btn.setText(t("btn_stop", lang))
        self._log_grp.setTitle(t("group_log", lang))
        # Only update status if idle
        if not self._pipeline:
            self.status_label.setText(t("status_ready", lang))
        self._gear_btn.setToolTip(t("btn_overlay_settings", lang))

    # --- Overlay settings ---

    def _open_overlay_settings(self):
        dlg = OverlaySettingsDialog(
            self._overlay.get_settings(), lang=self._lang, parent=self,
        )
        dlg.settings_changed.connect(self._overlay.apply_settings)
        if dlg.exec():
            self._overlay.apply_settings(dlg.get_settings())
            self._save_settings()

    # --- Settings persistence ---

    def _save_settings(self):
        data = {
            "device_name": self.device_combo.currentText(),
            "whisper_model": self.whisper_combo.currentText(),
            "input_language": self.input_lang_combo.currentIndex(),
            "target_languages": self._get_target_langs(),
            "buffer_preset": self.buffer_combo.currentIndex(),
            "ui_language": self._lang,
        }
        data.update(self._overlay.get_settings())
        save_settings(data)

    def _restore_settings(self):
        s = load_settings()
        if not s:
            return

        # UI language (set first so labels update)
        ui_lang = s.get("ui_language", "en")
        for i in range(self.lang_combo.count()):
            if self.lang_combo.itemData(i) == ui_lang:
                self.lang_combo.setCurrentIndex(i)
                break

        # Whisper model
        whisper = s.get("whisper_model")
        if whisper:
            idx = self.whisper_combo.findText(whisper)
            if idx >= 0:
                self.whisper_combo.setCurrentIndex(idx)

        # Input language
        input_idx = s.get("input_language")
        if isinstance(input_idx, int) and 0 <= input_idx < self.input_lang_combo.count():
            self.input_lang_combo.setCurrentIndex(input_idx)

        # Buffer preset
        buf_idx = s.get("buffer_preset")
        if isinstance(buf_idx, int) and 0 <= buf_idx < self.buffer_combo.count():
            self.buffer_combo.setCurrentIndex(buf_idx)

        # Target languages
        targets = s.get("target_languages")
        if isinstance(targets, list) and targets:
            for cb in self._target_cbs.values():
                cb.setChecked(False)
            for lang in targets:
                if lang in self._target_cbs:
                    self._target_cbs[lang].setChecked(True)

        # Device (match by name — index may change between reboots)
        device_name = s.get("device_name")
        if device_name:
            idx = self.device_combo.findText(device_name)
            if idx >= 0:
                self.device_combo.setCurrentIndex(idx)

        # Overlay appearance
        overlay_keys = {k: v for k, v in s.items() if k.startswith("overlay_")}
        if overlay_keys:
            self._overlay.apply_settings(overlay_keys)

    # --- Load helpers ---

    def _load_devices(self):
        self.device_combo.clear()
        devices = list_audio_devices()
        for idx, name in devices:
            self.device_combo.addItem(name, idx)

    def _get_target_langs(self) -> list[str]:
        """Return list of checked target languages."""
        return [lang for lang, cb in self._target_cbs.items() if cb.isChecked()]

    # --- Pipeline control ---

    def _on_start(self):
        device_idx = self.device_combo.currentData()
        if device_idx is None:
            QMessageBox.warning(self, t("err_title", self._lang),
                                t("err_no_device", self._lang))
            return

        target_langs = self._get_target_langs()
        if not target_langs:
            QMessageBox.warning(self, t("err_title", self._lang),
                                t("err_no_target", self._lang))
            return

        whisper_model = self.whisper_combo.currentText()
        ollama_model = OLLAMA_MODEL
        asr_language = self.input_lang_combo.currentData()
        source_lang_label = self.input_lang_combo.currentText()
        buf_max, buf_min = self.buffer_combo.currentData()

        self._save_settings()

        self.start_btn.setEnabled(False)
        self.status_label.setText(t("status_starting", self._lang))
        self.log_area.append(f"[INFO] Device: {self.device_combo.currentText()}")
        self.log_area.append(
            f"[INFO] Whisper: {whisper_model} | Ollama: {ollama_model}"
        )
        self.log_area.append(
            f"[INFO] Input: {source_lang_label} | Target: {', '.join(target_langs)}"
        )
        self.log_area.append(
            f"[INFO] Buffer: {self.buffer_combo.currentText()}"
        )
        self._auto_scroll()

        # Update overlay for selected targets
        self._overlay.update_target_langs(target_langs)

        self._pipeline = Pipeline(
            device_idx, whisper_model, ollama_model, target_langs,
            asr_language=asr_language,
            source_lang_label=source_lang_label,
            buffer_max_sec=buf_max,
            buffer_min_sec=buf_min,
        )
        self._pipeline.transcribed.connect(self._on_transcribed)
        self._pipeline.translated.connect(self._on_translated)
        self._pipeline.status.connect(self._on_status)
        self._pipeline.error.connect(self._on_error)
        self._pipeline.finished.connect(self._on_pipeline_finished)
        self._pipeline.start()

        self.stop_btn.setEnabled(True)
        self._set_controls_enabled(False)
        self._overlay.show()
        self._overlay.start_silence_timer()

    def _on_stop(self):
        if self._pipeline:
            self.status_label.setText(t("status_stopping", self._lang))
            self._pipeline.request_stop()
        else:
            self._finish_stop()

    def _set_controls_enabled(self, enabled: bool):
        self.device_combo.setEnabled(enabled)
        self.whisper_combo.setEnabled(enabled)
        self.input_lang_combo.setEnabled(enabled)
        self.buffer_combo.setEnabled(enabled)
        for cb in self._target_cbs.values():
            cb.setEnabled(enabled)

    # --- Signals ---

    def _on_transcribed(self, text: str):
        self._overlay.set_source(text)
        lang_code = self.input_lang_combo.currentData()
        lang_tag = (lang_code or "??").upper()
        self.log_area.append(f"[{lang_tag}] {text}")
        self._auto_scroll()

    def _on_translated(self, translations: dict):
        self._overlay.set_translations(translations)
        for lang, text in translations.items():
            tag = lang[:2].upper()
            self.log_area.append(f"  [{tag}] {text}")
        self.log_area.append("---")
        self._auto_scroll()

    def _on_status(self, msg: str):
        self.status_label.setText(msg)

    def _on_error(self, msg: str):
        self.status_label.setText(f"Error: {msg}")
        self.log_area.append(f"[ERROR] {msg}")
        self._auto_scroll()
        if self._pipeline:
            self._pipeline.request_stop()

    def _on_pipeline_finished(self):
        """Called when the pipeline QThread actually exits."""
        if self._pipeline:
            try:
                self._pipeline.transcribed.disconnect()
                self._pipeline.translated.disconnect()
                self._pipeline.status.disconnect()
                self._pipeline.error.disconnect()
                self._pipeline.finished.disconnect()
            except (RuntimeError, TypeError):
                pass
            self._pipeline = None
        self._finish_stop()

    def _finish_stop(self):
        """Reset UI after pipeline stops."""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self._set_controls_enabled(True)
        self._overlay.cancel_silence_timer()
        self._overlay.clear()
        self.status_label.setText(t("status_ready", self._lang))

    def _auto_scroll(self):
        scrollbar = self.log_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    # --- Cleanup ---

    def closeEvent(self, event):
        self._save_settings()
        if self._pipeline:
            self._pipeline.request_stop()
            self._pipeline.wait(3000)  # best-effort wait; process exit cleans up
            try:
                self._pipeline.transcribed.disconnect()
                self._pipeline.translated.disconnect()
                self._pipeline.status.disconnect()
                self._pipeline.error.disconnect()
                self._pipeline.finished.disconnect()
            except (RuntimeError, TypeError):
                pass
            self._pipeline = None
        self._overlay.close()
        event.accept()
