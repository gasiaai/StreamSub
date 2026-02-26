"""Transparent always-on-top subtitle overlay — auto-expands width, resizable corners."""

import re
from PyQt6.QtCore import Qt, QTimer, QRect
from PyQt6.QtGui import QFont, QFontMetrics, QColor, QPainter, QPainterPath
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QApplication

# Thai / CJK characters — no spaces between words, needs wrap hints
_WRAP_HINT_RE = re.compile(r'[\u0E00-\u0E7F\u3000-\u9FFF\uAC00-\uD7AF\uF900-\uFAFF]')

from config import (
    OVERLAY_WIDTH_DEFAULT,
    OVERLAY_WIDTH_MIN,
    OVERLAY_WIDTH_MAX_RATIO,
    OVERLAY_HEIGHT_BASE,
    OVERLAY_HEIGHT_PER_LANG,
    OVERLAY_FONT_MAX_SOURCE,
    OVERLAY_FONT_MAX_TRANS,
    OVERLAY_FONT_MIN,
    OVERLAY_FADE_TIMEOUT_MS,
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

_EDGE_MARGIN = 10  # pixels from edge to trigger resize cursor

_CURSOR_MAP = {
    "tl": Qt.CursorShape.SizeFDiagCursor,
    "br": Qt.CursorShape.SizeFDiagCursor,
    "tr": Qt.CursorShape.SizeBDiagCursor,
    "bl": Qt.CursorShape.SizeBDiagCursor,
    "l":  Qt.CursorShape.SizeHorCursor,
    "r":  Qt.CursorShape.SizeHorCursor,
    "t":  Qt.CursorShape.SizeVerCursor,
    "b":  Qt.CursorShape.SizeVerCursor,
}


class SubtitleOverlay(QWidget):
    """Frameless transparent overlay — auto-expands width, resizable by corners."""

    def __init__(self, target_langs: list[str] | None = None):
        super().__init__()
        self._target_langs = target_langs or ["English"]
        self._drag_pos = None
        self._resize_edge = None
        self._resize_start_pos = None
        self._resize_start_geo = None
        self._opacity = 1.0
        self._source_label = None
        self._trans_labels: dict[str, QLabel] = {}
        self._label_widths: dict[int, int] = {}  # label id → needed width
        self._layout = None
        self._max_width = 1200

        # --- Customizable appearance ---
        self._box_color = QColor(OVERLAY_BOX_COLOR_DEFAULT)
        self._box_opacity = OVERLAY_BG_OPACITY
        self._source_color_hex = OVERLAY_SOURCE_COLOR_DEFAULT
        self._source_opacity = OVERLAY_SOURCE_OPACITY_DEFAULT
        self._trans_color_hex = OVERLAY_TRANS_COLOR_DEFAULT
        self._trans_opacity = OVERLAY_TRANS_OPACITY_DEFAULT
        self._source_font_family = OVERLAY_SOURCE_FONT_DEFAULT
        self._trans_font_family = OVERLAY_TRANS_FONT_DEFAULT
        self._silence_fade_enabled = OVERLAY_SILENCE_FADE_DEFAULT
        self._silence_fade_timeout_ms = OVERLAY_SILENCE_TIMEOUT_DEFAULT * 1000

        self._setup_window()
        self._setup_ui()
        self._setup_fade_timer()
        self._calc_screen_limits()
        self._position_default()

    # --- Helpers ---

    @staticmethod
    def _hex_to_rgba(hex_color: str, alpha: int) -> str:
        """Convert '#RRGGBB' + alpha (0-255) to 'rgba(R, G, B, A)' string."""
        c = QColor(hex_color)
        return f"rgba({c.red()}, {c.green()}, {c.blue()}, {alpha})"

    def _calc_height(self) -> int:
        return OVERLAY_HEIGHT_BASE + len(self._target_langs) * OVERLAY_HEIGHT_PER_LANG

    def _calc_screen_limits(self):
        screen = QApplication.primaryScreen()
        if screen:
            self._max_width = int(screen.availableGeometry().width() * OVERLAY_WIDTH_MAX_RATIO)

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setMouseTracking(True)
        h = self._calc_height()
        self.setMinimumSize(OVERLAY_WIDTH_MIN, h)
        self.resize(OVERLAY_WIDTH_DEFAULT, h)

    def _setup_ui(self):
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 10, 16, 10)
        self._layout.setSpacing(2)
        self._build_labels()

    def _build_labels(self):
        """Create source label + one translation label per target language."""
        src_rgba = self._hex_to_rgba(self._source_color_hex, self._source_opacity)
        self._source_label = QLabel("")
        self._source_label.setWordWrap(True)
        self._source_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._source_label.setFont(QFont(self._source_font_family, OVERLAY_FONT_MAX_SOURCE))
        self._source_label.setStyleSheet(f"color: {src_rgba};")
        self._layout.addWidget(self._source_label)

        trans_rgba = self._hex_to_rgba(self._trans_color_hex, self._trans_opacity)
        self._trans_labels.clear()
        for i, lang in enumerate(self._target_langs):
            label = QLabel("")
            label.setWordWrap(True)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setFont(QFont(self._trans_font_family, OVERLAY_FONT_MAX_TRANS, QFont.Weight.Bold))
            label.setStyleSheet(f"color: {trans_rgba};")
            self._layout.addWidget(label)
            self._trans_labels[lang] = label

    def update_target_langs(self, target_langs: list[str]):
        """Rebuild labels for new target languages."""
        if self._source_label:
            self._source_label.setParent(None)
            self._source_label.deleteLater()
        for label in self._trans_labels.values():
            label.setParent(None)
            label.deleteLater()
        self._trans_labels.clear()
        self._label_widths.clear()

        self._target_langs = target_langs
        h = self._calc_height()
        self.setMinimumHeight(h)
        self.resize(OVERLAY_WIDTH_DEFAULT, h)
        self._build_labels()
        self._calc_screen_limits()
        self._position_default()

    def _setup_fade_timer(self):
        self._fade_timer = QTimer(self)
        self._fade_timer.setSingleShot(True)
        self._fade_timer.timeout.connect(self._start_fade)

        self._fade_step_timer = QTimer(self)
        self._fade_step_timer.setInterval(50)
        self._fade_step_timer.timeout.connect(self._fade_step)

        # Silence auto-fade timer
        self._silence_timer = QTimer(self)
        self._silence_timer.setSingleShot(True)
        self._silence_timer.timeout.connect(self._start_fade)

    def _position_default(self):
        """Place at bottom-center of primary screen."""
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.x() + (geo.width() - self.width()) // 2
            y = geo.y() + geo.height() - self.height() - 50
            self.move(x, y)

    # --- Font shrinking + auto-width ---

    @staticmethod
    def _add_wrap_hints(text: str) -> str:
        """Insert zero-width spaces after Thai/CJK chars so word-wrap can break them."""
        if not _WRAP_HINT_RE.search(text):
            return text
        out = []
        for ch in text:
            out.append(ch)
            if _WRAP_HINT_RE.match(ch):
                out.append('\u200b')
        return ''.join(out)

    def _fit_text(self, label: QLabel, text: str, max_size: int, avail_height: int):
        """Set text on label. Expands overlay width first, then shrinks font."""
        if not text:
            label.setText("")
            self._label_widths[id(label)] = OVERLAY_WIDTH_DEFAULT
            return

        display_text = self._add_wrap_hints(text)
        font = QFont(label.font())
        wrap_flag = int(Qt.TextFlag.TextWrapAnywhere)
        margins = 32

        # Step 1: Try max font at default width
        font.setPointSize(max_size)
        fm = QFontMetrics(font)
        rect = fm.boundingRect(
            0, 0, OVERLAY_WIDTH_DEFAULT - margins, 0, wrap_flag, display_text
        )
        if rect.height() <= avail_height:
            label.setFont(font)
            label.setText(display_text)
            self._label_widths[id(label)] = OVERLAY_WIDTH_DEFAULT
            return

        # Step 2: Try max font at max width
        rect_max = fm.boundingRect(
            0, 0, self._max_width - margins, 0, wrap_flag, display_text
        )
        if rect_max.height() <= avail_height:
            # Binary search for minimum width that fits at max font
            lo, hi = OVERLAY_WIDTH_DEFAULT, self._max_width
            while lo < hi:
                mid = (lo + hi) // 2
                r = fm.boundingRect(0, 0, mid - margins, 0, wrap_flag, display_text)
                if r.height() <= avail_height:
                    hi = mid
                else:
                    lo = mid + 1
            label.setFont(font)
            label.setText(display_text)
            self._label_widths[id(label)] = lo
            return

        # Step 3: At max width, shrink font
        max_avail = self._max_width - margins
        for size in range(max_size - 1, OVERLAY_FONT_MIN - 1, -1):
            font.setPointSize(size)
            fm = QFontMetrics(font)
            rect = fm.boundingRect(0, 0, max_avail, 0, wrap_flag, display_text)
            if rect.height() <= avail_height:
                label.setFont(font)
                label.setText(display_text)
                self._label_widths[id(label)] = self._max_width
                return

        # Fallback: min font, max width
        font.setPointSize(OVERLAY_FONT_MIN)
        label.setFont(font)
        label.setText(display_text)
        self._label_widths[id(label)] = self._max_width

    def _auto_resize_width(self):
        """Resize overlay to fit the widest label, keeping center position."""
        if not self._label_widths:
            return
        needed = max(self._label_widths.values())
        needed = max(needed, OVERLAY_WIDTH_DEFAULT)
        needed = min(needed, self._max_width)
        if needed == self.width():
            return
        # Keep horizontal center
        center_x = self.x() + self.width() // 2
        new_x = center_x - needed // 2
        self.setGeometry(new_x, self.y(), needed, self.height())

    def _get_height_alloc(self) -> tuple[int, int]:
        """Return (source_height, per_trans_height)."""
        usable = self.height() - 20 - 2 * len(self._target_langs)
        source_h = max(int(usable * 0.25), 20)
        n = len(self._target_langs) or 1
        trans_h = max((usable - source_h) // n, 20)
        return source_h, trans_h

    # --- Public API ---

    def set_source(self, text: str):
        source_h, _ = self._get_height_alloc()
        self._fit_text(self._source_label, text, OVERLAY_FONT_MAX_SOURCE, source_h)
        self._show_fresh()

    def set_translations(self, translations: dict):
        _, trans_h = self._get_height_alloc()
        for lang, text in translations.items():
            if lang in self._trans_labels:
                self._fit_text(self._trans_labels[lang], text, OVERLAY_FONT_MAX_TRANS, trans_h)
        self._show_fresh()

    def clear(self):
        if self._source_label:
            self._source_label.setText("")
        for label in self._trans_labels.values():
            label.setText("")
        self._label_widths.clear()
        self._silence_timer.stop()
        # Shrink back to default
        center_x = self.x() + self.width() // 2
        new_x = center_x - OVERLAY_WIDTH_DEFAULT // 2
        self.setGeometry(new_x, self.y(), OVERLAY_WIDTH_DEFAULT, self.height())

    # --- Settings API ---

    def apply_settings(self, settings: dict):
        """Apply overlay appearance settings from the settings dialog."""
        self._box_color = QColor(settings.get("overlay_box_color", OVERLAY_BOX_COLOR_DEFAULT))
        self._box_opacity = settings.get("overlay_box_opacity", OVERLAY_BG_OPACITY)
        self._source_color_hex = settings.get("overlay_source_color", OVERLAY_SOURCE_COLOR_DEFAULT)
        self._source_opacity = settings.get("overlay_source_opacity", OVERLAY_SOURCE_OPACITY_DEFAULT)
        self._trans_color_hex = settings.get("overlay_trans_color", OVERLAY_TRANS_COLOR_DEFAULT)
        self._trans_opacity = settings.get("overlay_trans_opacity", OVERLAY_TRANS_OPACITY_DEFAULT)
        self._source_font_family = settings.get("overlay_source_font", OVERLAY_SOURCE_FONT_DEFAULT)
        self._trans_font_family = settings.get("overlay_trans_font", OVERLAY_TRANS_FONT_DEFAULT)
        self._silence_fade_enabled = settings.get("overlay_silence_fade", OVERLAY_SILENCE_FADE_DEFAULT)
        self._silence_fade_timeout_ms = settings.get("overlay_silence_timeout", OVERLAY_SILENCE_TIMEOUT_DEFAULT) * 1000

        # Re-apply to existing labels
        if self._source_label:
            src_rgba = self._hex_to_rgba(self._source_color_hex, self._source_opacity)
            self._source_label.setStyleSheet(f"color: {src_rgba};")
            font = self._source_label.font()
            font.setFamily(self._source_font_family)
            self._source_label.setFont(font)

        trans_rgba = self._hex_to_rgba(self._trans_color_hex, self._trans_opacity)
        for label in self._trans_labels.values():
            label.setStyleSheet(f"color: {trans_rgba};")
            font = label.font()
            font.setFamily(self._trans_font_family)
            label.setFont(font)

        self.update()  # repaint for box color/opacity

    def get_settings(self) -> dict:
        """Return current overlay settings for persistence."""
        return {
            "overlay_box_color": self._box_color.name(),
            "overlay_box_opacity": self._box_opacity,
            "overlay_source_color": self._source_color_hex,
            "overlay_source_opacity": self._source_opacity,
            "overlay_trans_color": self._trans_color_hex,
            "overlay_trans_opacity": self._trans_opacity,
            "overlay_source_font": self._source_font_family,
            "overlay_trans_font": self._trans_font_family,
            "overlay_silence_fade": self._silence_fade_enabled,
            "overlay_silence_timeout": self._silence_fade_timeout_ms // 1000,
        }

    def start_silence_timer(self):
        """Start the silence fade timer. Called when pipeline starts."""
        if self._silence_fade_enabled and self._silence_fade_timeout_ms > 0:
            self._silence_timer.start(self._silence_fade_timeout_ms)

    def cancel_silence_timer(self):
        """Cancel the silence fade timer."""
        self._silence_timer.stop()

    # --- Fade logic ---

    def _show_fresh(self):
        self._auto_resize_width()
        self._opacity = 1.0
        self.setWindowOpacity(1.0)
        self._fade_step_timer.stop()
        self._fade_timer.stop()
        # Restart silence timer
        if self._silence_fade_enabled and self._silence_fade_timeout_ms > 0:
            self._silence_timer.stop()
            self._silence_timer.start(self._silence_fade_timeout_ms)
        if not self.isVisible():
            self.show()

    def _start_fade(self):
        self._fade_step_timer.start()

    def _fade_step(self):
        self._opacity -= 0.05
        if self._opacity <= 0:
            self._opacity = 0
            self._fade_step_timer.stop()
        self.setWindowOpacity(self._opacity)

    # --- Painting ---

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 12, 12)
        color = QColor(self._box_color)
        color.setAlpha(self._box_opacity)
        painter.fillPath(path, color)
        painter.end()

    # --- Edge / corner detection ---

    def _edge_at(self, pos) -> str | None:
        """Return edge/corner code at pos, or None."""
        x, y = pos.x(), pos.y()
        w, h = self.width(), self.height()
        m = _EDGE_MARGIN
        at_l = x < m
        at_r = x > w - m
        at_t = y < m
        at_b = y > h - m
        if at_t and at_l: return "tl"
        if at_t and at_r: return "tr"
        if at_b and at_l: return "bl"
        if at_b and at_r: return "br"
        if at_l: return "l"
        if at_r: return "r"
        if at_t: return "t"
        if at_b: return "b"
        return None

    # --- Mouse: drag + resize ---

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        edge = self._edge_at(event.position().toPoint())
        if edge:
            self._resize_edge = edge
            self._resize_start_pos = event.globalPosition().toPoint()
            self._resize_start_geo = self.geometry()
        else:
            self._drag_pos = event.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, event):
        gpos = event.globalPosition().toPoint()

        # --- Resizing ---
        if self._resize_edge and event.buttons() & Qt.MouseButton.LeftButton:
            delta = gpos - self._resize_start_pos
            geo = QRect(self._resize_start_geo)
            edge = self._resize_edge

            if edge in ("r", "tr", "br"):
                geo.setRight(self._resize_start_geo.right() + delta.x())
            if edge in ("l", "tl", "bl"):
                geo.setLeft(self._resize_start_geo.left() + delta.x())
            if edge in ("b", "bl", "br"):
                geo.setBottom(self._resize_start_geo.bottom() + delta.y())
            if edge in ("t", "tl", "tr"):
                geo.setTop(self._resize_start_geo.top() + delta.y())

            # Clamp width
            if geo.width() < OVERLAY_WIDTH_MIN:
                if "l" in edge:
                    geo.setLeft(geo.right() - OVERLAY_WIDTH_MIN)
                else:
                    geo.setRight(geo.left() + OVERLAY_WIDTH_MIN)
            if geo.width() > self._max_width:
                if "l" in edge:
                    geo.setLeft(geo.right() - self._max_width)
                else:
                    geo.setRight(geo.left() + self._max_width)

            # Clamp height (min = calculated height)
            min_h = self._calc_height()
            if geo.height() < min_h:
                if "t" in edge:
                    geo.setTop(geo.bottom() - min_h)
                else:
                    geo.setBottom(geo.top() + min_h)

            self.setGeometry(geo)
            return

        # --- Dragging ---
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(gpos - self._drag_pos)
            return

        # --- Hover: update cursor ---
        edge = self._edge_at(event.position().toPoint())
        if edge and edge in _CURSOR_MAP:
            self.setCursor(_CURSOR_MAP[edge])
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        self._resize_edge = None
        self._resize_start_pos = None
        self._resize_start_geo = None

    def mouseDoubleClickEvent(self, event):
        """Double-click to re-center and reset size."""
        self.resize(OVERLAY_WIDTH_DEFAULT, self._calc_height())
        self._position_default()
