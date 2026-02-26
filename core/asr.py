"""faster-whisper ASR with Silero VAD."""

import logging
import numpy as np

log = logging.getLogger(__name__)

from config import (
    WHISPER_DEVICE,
    WHISPER_COMPUTE_TYPE,
    ASR_LANGUAGE,
    ASR_BEAM_SIZE,
    ASR_VAD_FILTER,
    ASR_VAD_MIN_SILENCE_MS,
    ASR_VAD_SPEECH_PAD_MS,
    ASR_MIN_SEGMENT_LENGTH,
    MODEL_DIR,
)

# Prevent immediate garbage collection of CUDA models.
# ctranslate2's C++ destructor frees GPU memory, which can segfault when
# PyQt6 is still active (both fight over the CUDA context).
# Stashing old models here keeps them alive until process exit, where the
# OS/driver handles cleanup safely.
_deferred_models = []


class ASREngine:
    """Wraps faster-whisper for Japanese speech recognition."""

    def __init__(self, model_size: str = "large-v3-turbo"):
        self._model = None
        self._model_size = model_size
        self.device_used = None
        self.compute_used = None

    def load(self, status_callback=None):
        """Load model onto GPU (with CPU fallback). Call once at startup."""
        def _status(msg):
            log.info(msg)
            if status_callback:
                status_callback(msg)

        from faster_whisper import WhisperModel

        attempts = [
            (WHISPER_DEVICE, WHISPER_COMPUTE_TYPE),
            ("cuda", "int8"),
            ("cpu", "int8"),
        ]

        last_err = None
        for device, compute in attempts:
            try:
                _status(f"Loading Whisper on {device}/{compute}...")
                self._model = WhisperModel(
                    self._model_size,
                    device=device,
                    compute_type=compute,
                    download_root=MODEL_DIR,
                )
                self.device_used = device
                self.compute_used = compute
                _status(f"Whisper ready — {device}/{compute}")
                return
            except Exception as e:
                last_err = e
                log.warning("Failed %s/%s: %s", device, compute, e)
                continue

        raise RuntimeError(f"Could not load Whisper: {last_err}")

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def transcribe(self, audio: np.ndarray, language: str | None = ASR_LANGUAGE) -> str:
        """
        Transcribe a float32 16kHz mono audio array to text.
        language: Whisper language code (e.g. "ja", "zh") or None for auto-detect.
        Returns empty string if nothing detected.
        """
        if self._model is None:
            raise RuntimeError("ASR model not loaded — call load() first")

        if len(audio) < 1600:  # < 0.1s
            return ""

        segments, info = self._model.transcribe(
            audio,
            language=language,
            beam_size=ASR_BEAM_SIZE,
            vad_filter=ASR_VAD_FILTER,
            vad_parameters=dict(
                min_silence_duration_ms=ASR_VAD_MIN_SILENCE_MS,
                speech_pad_ms=ASR_VAD_SPEECH_PAD_MS,
            ),
        )

        texts = []
        for seg in segments:
            duration = seg.end - seg.start
            if duration < ASR_MIN_SEGMENT_LENGTH:
                continue

            # Skip segments where Whisper thinks there's no speech.
            # Threshold 0.4 filters most hallucinations during silence
            # while keeping real speech that Whisper is confident about.
            if seg.no_speech_prob > 0.4:
                log.debug("Skipping segment (no_speech_prob=%.2f): %s",
                          seg.no_speech_prob, seg.text[:60])
                continue

            text = seg.text.strip()
            if text:
                texts.append(text)

        return " ".join(texts)

    def unload(self):
        """Mark model as logically unloaded.

        The actual ctranslate2 model object is stashed in _deferred_models
        to prevent immediate garbage collection.  The C++ destructor that
        frees CUDA memory segfaults when PyQt6 is still running (both
        libraries share the CUDA context).  Deferring to process exit
        lets the OS reclaim GPU memory safely.
        """
        if self._model is not None:
            _deferred_models.append(self._model)
            self._model = None
