"""Persist user settings to a JSON file next to main.py."""

import json
import logging
import os

log = logging.getLogger(__name__)

_APP_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(_APP_DIR, "settings.json")


def load_settings() -> dict:
    """Load settings from JSON. Returns empty dict if missing or corrupt."""
    if not os.path.exists(SETTINGS_FILE):
        return {}
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception as e:
        log.warning("Failed to load settings: %s", e)
    return {}


def save_settings(data: dict):
    """Write settings dict to JSON."""
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.warning("Failed to save settings: %s", e)
