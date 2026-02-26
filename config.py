import os
from dotenv import load_dotenv

load_dotenv()

APP_VERSION = "1.0.1"

# --- Audio ---
SAMPLE_RATE = 16000
CHANNELS = 1
BLOCK_DURATION_MS = 30  # ms per audio callback block

# --- ASR (faster-whisper) ---
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "large-v3-turbo")
WHISPER_DEVICE = "cuda"
WHISPER_COMPUTE_TYPE = "float16"
ASR_LANGUAGE = "ja"  # default — overridden by UI dropdown

# Whisper-supported input languages
INPUT_LANGUAGES = [
    ("Japanese",   "ja"),
    ("Chinese",    "zh"),
    ("Korean",     "ko"),
    ("English",    "en"),
    ("Thai",       "th"),
    ("Spanish",    "es"),
    ("French",     "fr"),
    ("German",     "de"),
    ("Russian",    "ru"),
    ("Portuguese", "pt"),
    ("Italian",    "it"),
    ("Vietnamese", "vi"),
    ("Indonesian", "id"),
    ("Auto-detect", None),
]
ASR_BEAM_SIZE = 5
ASR_VAD_FILTER = True
ASR_VAD_MIN_SILENCE_MS = 500
ASR_VAD_SPEECH_PAD_MS = 200
ASR_MIN_SEGMENT_LENGTH = 0.5  # seconds — skip very short segments

# --- Ollama Translation ---
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "scb10x/typhoon-translate1.5-4b")
OLLAMA_TIMEOUT = 15  # seconds per translation request

TRANSLATION_PROMPT = """You are a translator. Translate the following {source_lang} text into {lang} ({lang_native}).
Rules:
- Output ONLY the {lang} translation, nothing else
- You MUST write entirely in {lang_script} script — do NOT use any other language or script
- Keep names and proper nouns as-is
- If the text is unclear or fragmented, translate what you can
- Keep it natural and conversational"""

# Map target language → native name + script name for stronger prompting
TARGET_LANG_META = {
    "English":    {"native": "English",          "script": "Latin/English"},
    "Thai":       {"native": "ภาษาไทย",          "script": "Thai (อักษรไทย)"},
    "Japanese":   {"native": "日本語",            "script": "Japanese (漢字/ひらがな/カタカナ)"},
    "Chinese":    {"native": "中文",              "script": "Chinese (汉字)"},
    "Korean":     {"native": "한국어",             "script": "Korean (한글)"},
    "Spanish":    {"native": "Español",          "script": "Latin/Spanish"},
    "French":     {"native": "Français",         "script": "Latin/French"},
    "German":     {"native": "Deutsch",          "script": "Latin/German"},
    "Russian":    {"native": "Русский",          "script": "Cyrillic (кириллица)"},
    "Portuguese": {"native": "Português",        "script": "Latin/Portuguese"},
    "Italian":    {"native": "Italiano",         "script": "Latin/Italian"},
    "Vietnamese": {"native": "Tiếng Việt",       "script": "Latin/Vietnamese"},
    "Indonesian": {"native": "Bahasa Indonesia", "script": "Latin/Indonesian"},
}

# Ordered list for UI dropdown
TARGET_LANGUAGES = list(TARGET_LANG_META.keys())

# --- Audio Buffer ---
AUDIO_BUFFER_MAX_SEC = 5.0  # default — overridden by UI dropdown
AUDIO_BUFFER_MIN_SEC = 2.0  # default — overridden by UI dropdown

# Presets: (label, max_sec, min_sec)
BUFFER_PRESETS = [
    ("Fast (3s)",     3.0, 1.0),
    ("Balanced (5s)", 5.0, 2.0),
    ("Accurate (8s)", 8.0, 3.0),
]

# --- Overlay UI ---
OVERLAY_WIDTH_DEFAULT = 700     # starting width (auto-expands for long text)
OVERLAY_WIDTH_MIN = 350         # minimum width (manual resize floor)
OVERLAY_WIDTH_MAX_RATIO = 0.7   # max width = 70% of screen width
OVERLAY_HEIGHT_BASE = 80        # base height (source label area)
OVERLAY_HEIGHT_PER_LANG = 70    # extra height per target language
OVERLAY_FONT_MAX_SOURCE = 14    # max font size for source text
OVERLAY_FONT_MAX_TRANS = 22     # max font size for translated text
OVERLAY_FONT_MIN = 6            # minimum font size floor
OVERLAY_FADE_TIMEOUT_MS = 8000
OVERLAY_BG_OPACITY = 180  # 0-255

# Overlay appearance defaults (overridden by user settings)
OVERLAY_BOX_COLOR_DEFAULT = "#18181b"
OVERLAY_SOURCE_COLOR_DEFAULT = "#c8c8c8"
OVERLAY_SOURCE_OPACITY_DEFAULT = 180
OVERLAY_TRANS_COLOR_DEFAULT = "#ffffff"
OVERLAY_TRANS_OPACITY_DEFAULT = 255
OVERLAY_SOURCE_FONT_DEFAULT = "Meiryo"
OVERLAY_TRANS_FONT_DEFAULT = "Segoe UI"
OVERLAY_SILENCE_FADE_DEFAULT = False
OVERLAY_SILENCE_TIMEOUT_DEFAULT = 10  # seconds

# --- Whisper model storage ---
MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Model")
