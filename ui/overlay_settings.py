"""Overlay appearance settings dialog."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFontDatabase
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QPushButton, QSlider, QComboBox, QCheckBox, QSpinBox,
    QColorDialog,
)

from config import (
    OVERLAY_BG_OPACITY,
    OVERLAY_BOX_COLOR_DEFAULT,
    OVERLAY_SOURCE_COLOR_DEFAULT,
    OVERLAY_SOURCE_OPACITY_DEFAULT,
    OVERLAY_TRANS_COLOR_DEFAULT,
    OVERLAY_TRANS_OPACITY_DEFAULT,
    OVERLAY_SOURCE_FONT_DEFAULT,
    OVERLAY_TRANS_FONT_DEFAULT,
    OVERLAY_SILENCE_FADE_DEFAULT,
    OVERLAY_SILENCE_TIMEOUT_DEFAULT,
)
from ui.translations import t

_DIALOG_STYLE = """
QDialog {
    background-color: #18181b;
    color: #ffffff;
    font-family: "Segoe UI";
}
QLabel { color: #ffffff; }
QSlider::groove:horizontal {
    height: 6px;
    background: #3f3f46;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    width: 16px;
    margin: -5px 0;
    background: #facc15;
    border-radius: 8px;
}
QComboBox, QSpinBox {
    background-color: #27272a;
    border: 1px solid #52525b;
    border-radius: 4px;
    padding: 4px 8px;
    color: #ffffff;
}
QComboBox QAbstractItemView {
    background-color: #27272a;
    color: #ffffff;
    selection-background-color: #facc15;
    selection-color: #18181b;
}
QPushButton {
    background-color: #27272a;
    border: 1px solid #52525b;
    border-radius: 4px;
    padding: 6px 14px;
    color: #ffffff;
}
QPushButton:hover { border-color: #a1a1aa; }
QPushButton#okBtn {
    background-color: #16a34a;
    color: white;
    font-weight: bold;
}
QPushButton#okBtn:hover { background-color: #15803d; }
QCheckBox { spacing: 6px; color: #ffffff; }
QCheckBox::indicator {
    width: 16px; height: 16px;
    border: 2px solid #71717a;
    border-radius: 3px;
    background: transparent;
}
QCheckBox::indicator:checked {
    background: #facc15;
    border-color: #facc15;
}
"""


class ColorButton(QPushButton):
    """Button that shows its color and opens QColorDialog on click."""

    color_changed = pyqtSignal(str)  # emits hex "#RRGGBB"

    def __init__(self, initial_color: str = "#ffffff", parent=None):
        super().__init__(parent)
        self._color = initial_color
        self.setFixedSize(40, 28)
        self._update_style()
        self.clicked.connect(self._pick_color)

    def _update_style(self):
        self.setStyleSheet(
            f"background-color: {self._color}; "
            f"border: 1px solid #71717a; border-radius: 4px; "
            f"min-height: 0; padding: 0;"
        )

    def _pick_color(self):
        dlg = QColorDialog(QColor(self._color))  # no parent — avoid dark stylesheet leak
        if dlg.exec() == QColorDialog.DialogCode.Accepted:
            self._color = dlg.currentColor().name()
            self._update_style()
            self.color_changed.emit(self._color)

    def color(self) -> str:
        return self._color

    def set_color(self, hex_color: str):
        self._color = hex_color
        self._update_style()


class OverlaySettingsDialog(QDialog):
    """Modal dialog for overlay appearance settings with live preview."""

    settings_changed = pyqtSignal(dict)

    def __init__(self, current_settings: dict, lang: str = "en", parent=None):
        super().__init__(parent)
        self._lang = lang
        self._settings = dict(current_settings)
        self.setWindowTitle(t("dlg_overlay_title", lang))
        self.setMinimumWidth(400)
        self.setStyleSheet(_DIALOG_STYLE)
        self._setup_ui()
        self._populate(current_settings)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        form = QFormLayout()
        form.setSpacing(8)

        # --- Box color + opacity ---
        box_row = QHBoxLayout()
        self._box_color_btn = ColorButton()
        self._box_opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self._box_opacity_slider.setRange(0, 255)
        self._box_opacity_lbl = QLabel()
        self._box_opacity_lbl.setFixedWidth(28)
        box_row.addWidget(self._box_color_btn)
        box_row.addWidget(self._box_opacity_slider, 1)
        box_row.addWidget(self._box_opacity_lbl)
        form.addRow(t("dlg_box_color", self._lang), box_row)

        # --- Source text color + opacity ---
        src_row = QHBoxLayout()
        self._src_color_btn = ColorButton()
        self._src_opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self._src_opacity_slider.setRange(0, 255)
        self._src_opacity_lbl = QLabel()
        self._src_opacity_lbl.setFixedWidth(28)
        src_row.addWidget(self._src_color_btn)
        src_row.addWidget(self._src_opacity_slider, 1)
        src_row.addWidget(self._src_opacity_lbl)
        form.addRow(t("dlg_source_color", self._lang), src_row)

        # --- Translation text color + opacity ---
        trans_row = QHBoxLayout()
        self._trans_color_btn = ColorButton()
        self._trans_opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self._trans_opacity_slider.setRange(0, 255)
        self._trans_opacity_lbl = QLabel()
        self._trans_opacity_lbl.setFixedWidth(28)
        trans_row.addWidget(self._trans_color_btn)
        trans_row.addWidget(self._trans_opacity_slider, 1)
        trans_row.addWidget(self._trans_opacity_lbl)
        form.addRow(t("dlg_trans_color", self._lang), trans_row)

        # --- Fonts ---
        families = QFontDatabase.families()

        self._src_font_combo = QComboBox()
        self._src_font_combo.addItems(families)
        form.addRow(t("dlg_source_font", self._lang), self._src_font_combo)

        self._trans_font_combo = QComboBox()
        self._trans_font_combo.addItems(families)
        form.addRow(t("dlg_trans_font", self._lang), self._trans_font_combo)

        layout.addLayout(form)

        # --- Silence auto-fade ---
        fade_row = QHBoxLayout()
        self._fade_cb = QCheckBox(t("dlg_silence_fade", self._lang))
        fade_row.addWidget(self._fade_cb)
        fade_row.addStretch()
        fade_row.addWidget(QLabel(t("dlg_silence_timeout", self._lang)))
        self._fade_spin = QSpinBox()
        self._fade_spin.setRange(3, 120)
        self._fade_spin.setSuffix(" s")
        fade_row.addWidget(self._fade_spin)
        layout.addLayout(fade_row)

        # --- Buttons ---
        btn_row = QHBoxLayout()
        reset_btn = QPushButton(t("dlg_reset_defaults", self._lang))
        reset_btn.clicked.connect(self._reset_defaults)
        btn_row.addWidget(reset_btn)
        btn_row.addStretch()
        ok_btn = QPushButton("OK")
        ok_btn.setObjectName("okBtn")
        ok_btn.clicked.connect(self._on_ok)
        btn_row.addWidget(ok_btn)
        layout.addLayout(btn_row)

        # --- Live preview connections ---
        self._box_color_btn.color_changed.connect(lambda _: self._emit_live())
        self._box_opacity_slider.valueChanged.connect(self._on_box_opacity)
        self._src_color_btn.color_changed.connect(lambda _: self._emit_live())
        self._src_opacity_slider.valueChanged.connect(self._on_src_opacity)
        self._trans_color_btn.color_changed.connect(lambda _: self._emit_live())
        self._trans_opacity_slider.valueChanged.connect(self._on_trans_opacity)
        self._src_font_combo.currentTextChanged.connect(lambda _: self._emit_live())
        self._trans_font_combo.currentTextChanged.connect(lambda _: self._emit_live())
        self._fade_cb.stateChanged.connect(lambda _: self._emit_live())
        self._fade_spin.valueChanged.connect(lambda _: self._emit_live())

    # --- Slider label updates ---

    def _on_box_opacity(self, v):
        self._box_opacity_lbl.setText(str(v))
        self._emit_live()

    def _on_src_opacity(self, v):
        self._src_opacity_lbl.setText(str(v))
        self._emit_live()

    def _on_trans_opacity(self, v):
        self._trans_opacity_lbl.setText(str(v))
        self._emit_live()

    # --- Gather / emit ---

    def _gather(self) -> dict:
        return {
            "overlay_box_color": self._box_color_btn.color(),
            "overlay_box_opacity": self._box_opacity_slider.value(),
            "overlay_source_color": self._src_color_btn.color(),
            "overlay_source_opacity": self._src_opacity_slider.value(),
            "overlay_trans_color": self._trans_color_btn.color(),
            "overlay_trans_opacity": self._trans_opacity_slider.value(),
            "overlay_source_font": self._src_font_combo.currentText(),
            "overlay_trans_font": self._trans_font_combo.currentText(),
            "overlay_silence_fade": self._fade_cb.isChecked(),
            "overlay_silence_timeout": self._fade_spin.value(),
        }

    def _emit_live(self):
        self.settings_changed.emit(self._gather())

    def _populate(self, s: dict):
        self._box_color_btn.set_color(s.get("overlay_box_color", OVERLAY_BOX_COLOR_DEFAULT))
        self._box_opacity_slider.setValue(s.get("overlay_box_opacity", OVERLAY_BG_OPACITY))
        self._box_opacity_lbl.setText(str(self._box_opacity_slider.value()))

        self._src_color_btn.set_color(s.get("overlay_source_color", OVERLAY_SOURCE_COLOR_DEFAULT))
        self._src_opacity_slider.setValue(s.get("overlay_source_opacity", OVERLAY_SOURCE_OPACITY_DEFAULT))
        self._src_opacity_lbl.setText(str(self._src_opacity_slider.value()))

        self._trans_color_btn.set_color(s.get("overlay_trans_color", OVERLAY_TRANS_COLOR_DEFAULT))
        self._trans_opacity_slider.setValue(s.get("overlay_trans_opacity", OVERLAY_TRANS_OPACITY_DEFAULT))
        self._trans_opacity_lbl.setText(str(self._trans_opacity_slider.value()))

        idx = self._src_font_combo.findText(s.get("overlay_source_font", OVERLAY_SOURCE_FONT_DEFAULT))
        if idx >= 0:
            self._src_font_combo.setCurrentIndex(idx)

        idx = self._trans_font_combo.findText(s.get("overlay_trans_font", OVERLAY_TRANS_FONT_DEFAULT))
        if idx >= 0:
            self._trans_font_combo.setCurrentIndex(idx)

        self._fade_cb.setChecked(s.get("overlay_silence_fade", OVERLAY_SILENCE_FADE_DEFAULT))
        self._fade_spin.setValue(s.get("overlay_silence_timeout", OVERLAY_SILENCE_TIMEOUT_DEFAULT))

    def _reset_defaults(self):
        defaults = {
            "overlay_box_color": OVERLAY_BOX_COLOR_DEFAULT,
            "overlay_box_opacity": OVERLAY_BG_OPACITY,
            "overlay_source_color": OVERLAY_SOURCE_COLOR_DEFAULT,
            "overlay_source_opacity": OVERLAY_SOURCE_OPACITY_DEFAULT,
            "overlay_trans_color": OVERLAY_TRANS_COLOR_DEFAULT,
            "overlay_trans_opacity": OVERLAY_TRANS_OPACITY_DEFAULT,
            "overlay_source_font": OVERLAY_SOURCE_FONT_DEFAULT,
            "overlay_trans_font": OVERLAY_TRANS_FONT_DEFAULT,
            "overlay_silence_fade": OVERLAY_SILENCE_FADE_DEFAULT,
            "overlay_silence_timeout": OVERLAY_SILENCE_TIMEOUT_DEFAULT,
        }
        self._populate(defaults)
        self.settings_changed.emit(defaults)

    def _on_ok(self):
        self._settings = self._gather()
        self.accept()

    def get_settings(self) -> dict:
        return self._settings
