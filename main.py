"""StreamSub — Real-time speech translation overlay for streamers."""

import sys
import os
import traceback
import logging

# Ensure project root is on path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# --- CRITICAL: import ctranslate2 BEFORE PyQt6 ---
# PyQt6 and ctranslate2 both init CUDA (faster-whisper uses ctranslate2).
# If PyQt6 goes first, ctranslate2 segfaults. Pre-importing fixes this.
try:
    import ctranslate2  # noqa: F401
except ImportError:
    pass  # ctranslate2 is pulled in by faster-whisper anyway

_log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "streamsub.log")
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr),
        logging.FileHandler(_log_file, mode="w", encoding="utf-8"),
    ],
)
log = logging.getLogger("streamsub")

# Silence noisy 3rd-party loggers
for _name in ("httpcore", "httpx", "urllib3", "huggingface_hub",
              "faster_whisper", "ctranslate2", "numba"):
    logging.getLogger(_name).setLevel(logging.WARNING)


def global_exception_handler(exc_type, exc_value, exc_tb):
    """Catch any unhandled exception so the app doesn't vanish silently."""
    msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    log.critical("Unhandled exception:\n%s", msg)
    try:
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.critical(None, "Fatal Error", msg)
    except Exception:
        pass
    sys.__excepthook__(exc_type, exc_value, exc_tb)


sys.excepthook = global_exception_handler


def main():
    from PyQt6.QtWidgets import QApplication
    from ui.control_panel import ControlPanel

    app = QApplication(sys.argv)
    app.setApplicationName("StreamSub")

    panel = ControlPanel()
    panel.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
