"""Ollama-based translation via HTTP API."""

import logging
import re
import requests

from config import (
    OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT,
    TRANSLATION_PROMPT, TARGET_LANG_META,
)

log = logging.getLogger(__name__)

# Regex to strip leaked CJK characters from non-CJK target languages
_CJK_RE = re.compile(
    r'[\u3000-\u303F'   # CJK punctuation
    r'\u3040-\u309F'     # Hiragana
    r'\u30A0-\u30FF'     # Katakana
    r'\u3400-\u4DBF'     # CJK Extension A
    r'\u4E00-\u9FFF'     # CJK Unified Ideographs
    r'\uF900-\uFAFF]'    # CJK Compatibility Ideographs
)

# Languages whose output is expected to contain CJK characters
_CJK_TARGETS = {"Chinese", "Japanese", "Korean"}

# Thai script regex — strip leaked Thai from non-Thai targets
_THAI_RE = re.compile(r'[\u0E00-\u0E7F]')
_THAI_TARGETS = {"Thai"}


def list_ollama_models() -> list[str]:
    """Return list of locally available Ollama model names."""
    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        r.raise_for_status()
        return [m["name"] for m in r.json().get("models", [])]
    except Exception as e:
        log.warning("Could not list Ollama models: %s", e)
        return []


def ensure_ollama_model(model: str = OLLAMA_MODEL, status_callback=None):
    """Check if model exists locally; if not, pull it with progress."""
    def _status(msg):
        log.info(msg)
        if status_callback:
            status_callback(msg)

    # Check if already available
    local = list_ollama_models()
    # Ollama may store as "qwen2.5:latest" — match base name
    base = model.split(":")[0]
    if any(base in m for m in local):
        _status(f"Ollama model '{model}' is ready.")
        return

    _status(f"Pulling Ollama model '{model}' (first run)...")
    try:
        r = requests.post(
            f"{OLLAMA_BASE_URL}/api/pull",
            json={"name": model, "stream": True},
            stream=True,
            timeout=600,
        )
        r.raise_for_status()
        for line in r.iter_lines():
            if line:
                import json
                data = json.loads(line)
                st = data.get("status", "")
                if "pulling" in st or "download" in st.lower():
                    total = data.get("total", 0)
                    completed = data.get("completed", 0)
                    if total > 0:
                        pct = completed / total * 100
                        _status(f"Downloading {model}: {pct:.0f}%")
                    else:
                        _status(f"Downloading {model}...")
                elif st == "success":
                    _status(f"Model '{model}' ready.")
    except Exception as e:
        raise RuntimeError(f"Failed to pull model '{model}': {e}") from e


class Translator:
    """Translates text using Ollama HTTP API."""

    def __init__(self, model: str = OLLAMA_MODEL,
                 target_lang: str = "English",
                 source_lang: str = "Japanese",
                 base_url: str = OLLAMA_BASE_URL):
        self.model = model
        self.target_lang = target_lang
        self.source_lang = source_lang
        self.base_url = base_url
        self._session = requests.Session()

        # Build system prompt with language metadata
        meta = TARGET_LANG_META.get(target_lang, {})
        self._system_prompt = TRANSLATION_PROMPT.format(
            source_lang=source_lang,
            lang=target_lang,
            lang_native=meta.get("native", target_lang),
            lang_script=meta.get("script", target_lang),
        )

    def translate(self, text: str) -> str:
        """Translate text and return the result. Returns empty string on failure."""
        if not text.strip():
            return ""

        try:
            r = self._session.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "system": self._system_prompt,
                    "prompt": text,
                    "stream": False,
                },
                timeout=OLLAMA_TIMEOUT,
            )
            r.raise_for_status()
            result = r.json().get("response", "").strip()
            return self._clean_result(result)
        except Exception as e:
            log.error("Translation error: %s", e)
            return f"[Translation error: {e}]"

    def _clean_result(self, text: str) -> str:
        """Post-process translation result."""
        # Strip leaked CJK characters from non-CJK target languages
        if self.target_lang not in _CJK_TARGETS:
            text = _CJK_RE.sub("", text)
        # Strip leaked Thai characters from non-Thai target languages
        if self.target_lang not in _THAI_TARGETS:
            text = _THAI_RE.sub("", text)
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def close_session(self):
        """Close the HTTP session to unblock any pending request."""
        try:
            self._session.close()
        except Exception:
            pass
