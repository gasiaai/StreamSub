"""Real-time pipeline: audio → ASR → translate → display."""

import logging
import queue
import time
import traceback
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

from config import SAMPLE_RATE, AUDIO_BUFFER_MAX_SEC, AUDIO_BUFFER_MIN_SEC
from core.audio import AudioCapture
from core.asr import ASREngine
from core.translator import Translator, ensure_ollama_model, TranslationTimeout

log = logging.getLogger(__name__)


class Pipeline(QThread):
    """Orchestrator thread — captures audio, runs ASR, translates to multiple targets."""

    transcribed = pyqtSignal(str)    # Source language text
    translated  = pyqtSignal(dict)   # {lang: translated_text}
    status      = pyqtSignal(str)    # Status messages
    error       = pyqtSignal(str)    # Error messages

    def __init__(self, device_index: int, whisper_model: str,
                 ollama_model: str, target_langs: list[str],
                 asr_language: str | None = "ja",
                 source_lang_label: str = "Japanese",
                 buffer_max_sec: float = AUDIO_BUFFER_MAX_SEC,
                 buffer_min_sec: float = AUDIO_BUFFER_MIN_SEC):
        super().__init__()
        self.device_index = device_index
        self.whisper_model = whisper_model
        self.ollama_model = ollama_model
        self.target_langs = target_langs
        self.asr_language = asr_language
        self.source_lang_label = source_lang_label
        self.buffer_max_sec = buffer_max_sec
        self.buffer_min_sec = buffer_min_sec
        self._stop_flag = False
        self._translators: dict[str, Translator] = {}
        self._pending_text = ""  # accumulated source text from timed-out rounds

    def run(self):
        """Top-level run — everything wrapped so no exception kills the process."""
        try:
            self._run_pipeline()
        except BaseException as e:
            msg = f"{type(e).__name__}: {e}"
            log.critical("Pipeline crashed:\n%s", traceback.format_exc())
            try:
                self.error.emit(msg)
            except (RuntimeError, OSError):
                pass  # Qt objects may already be gone

    def _run_pipeline(self):
        audio_queue = queue.Queue()
        asr = None
        capture = None

        # --- Init ASR ---
        self.status.emit("Loading Whisper model...")
        log.info("Loading Whisper model: %s", self.whisper_model)
        try:
            asr = ASREngine(self.whisper_model)
            asr.load(status_callback=lambda msg: self.status.emit(msg))
        except Exception as e:
            log.error("Whisper load failed: %s", e, exc_info=True)
            self.error.emit(f"Failed to load Whisper: {e}")
            return
        log.info("Whisper loaded successfully")

        if self._stop_flag:
            asr.unload()
            return

        # --- Ensure Ollama model is available (auto-pull on first run) ---
        self.status.emit(f"Checking Ollama model '{self.ollama_model}'...")
        try:
            ensure_ollama_model(
                self.ollama_model,
                status_callback=lambda msg: self.status.emit(msg),
            )
        except Exception as e:
            log.error("Ollama model check failed: %s", e, exc_info=True)
            self.error.emit(f"Ollama model error: {e}")
            asr.unload()
            return

        if self._stop_flag:
            asr.unload()
            return

        # --- Init Translators (one per target language) ---
        self.status.emit("Initializing translators...")
        for lang in self.target_langs:
            self._translators[lang] = Translator(
                model=self.ollama_model,
                target_lang=lang,
                source_lang=self.source_lang_label,
            )
        log.info("Translators ready: %s", list(self._translators.keys()))

        # --- Init Audio Capture ---
        self.status.emit("Starting audio capture...")
        capture = AudioCapture(self.device_index, audio_queue)
        try:
            capture.start()  # blocks until stream confirmed running
        except Exception as e:
            log.error("Audio capture failed: %s", e, exc_info=True)
            self.error.emit(f"Audio capture failed: {e}")
            asr.unload()
            return

        if self._stop_flag:
            capture.stop()
            asr.unload()
            return

        self.status.emit("Listening...")
        log.info("Pipeline running — listening on device %d", self.device_index)

        # --- Main loop ---
        audio_buffer = []
        buffer_samples = 0
        last_speech_time = time.monotonic()
        silence_threshold = 1.5  # seconds of silence to trigger ASR

        try:
            while not self._stop_flag:
                # Drain audio queue
                try:
                    msg_type, data = audio_queue.get(timeout=0.1)
                except queue.Empty:
                    self._check_flush(audio_buffer, buffer_samples, asr,
                                      last_speech_time, silence_threshold)
                    if not audio_buffer:
                        buffer_samples = 0
                    continue

                if msg_type == "error":
                    self.error.emit(f"Audio error: {data}")
                    break

                if msg_type == "audio":
                    chunk = data
                    energy = float(np.sqrt(np.mean(chunk ** 2)))

                    if energy > 0.005:  # speech detected
                        last_speech_time = time.monotonic()
                        audio_buffer.append(chunk)
                        buffer_samples += len(chunk)
                    else:
                        # Silence — don't buffer, just check flush
                        pass

                    total_sec = buffer_samples / SAMPLE_RATE

                    # Force flush if buffer is full
                    if total_sec >= self.buffer_max_sec:
                        self._process_buffer(audio_buffer, buffer_samples, asr)
                        audio_buffer.clear()
                        buffer_samples = 0
                        last_speech_time = time.monotonic()
                        continue

                    # Flush on silence
                    self._check_flush(audio_buffer, buffer_samples, asr,
                                      last_speech_time, silence_threshold)
                    if not audio_buffer:
                        buffer_samples = 0

        finally:
            # --- Cleanup: all on pipeline thread (thread-safe) ---
            log.info("Pipeline shutting down...")

            # 1. Close translator HTTP sessions (same thread = safe)
            for translator in self._translators.values():
                try:
                    translator.close_session()
                except Exception:
                    pass

            # 2. Stop audio capture
            if capture is not None:
                try:
                    capture.stop()
                except Exception as e:
                    log.warning("Error stopping audio capture: %s", e)

            # 3. Unload ASR model (deferred — see asr.py)
            if asr is not None:
                try:
                    log.info("Unloading ASR model...")
                    asr.unload()
                    log.info("ASR model unloaded")
                except Exception as e:
                    log.warning("Error unloading ASR: %s", e)

            # 4. Notify UI
            try:
                self.status.emit("Stopped.")
            except (RuntimeError, OSError):
                pass  # Qt objects may already be gone

            log.info("Pipeline stopped cleanly")
            # Flush log so message appears even if process exits soon after
            for handler in logging.getLogger().handlers:
                try:
                    handler.flush()
                except Exception:
                    pass

    def _check_flush(self, audio_buffer, buffer_samples, asr,
                     last_speech_time, silence_threshold):
        """Flush buffer if enough silence has passed and buffer has enough audio."""
        if not audio_buffer:
            return
        total_sec = buffer_samples / SAMPLE_RATE
        silence_dur = time.monotonic() - last_speech_time
        if total_sec >= self.buffer_min_sec and silence_dur >= silence_threshold:
            self._process_buffer(audio_buffer, buffer_samples, asr)
            audio_buffer.clear()

    def _process_buffer(self, audio_buffer, buffer_samples, asr):
        """Run ASR + translation on accumulated audio."""
        if not audio_buffer:
            return

        audio = np.concatenate(audio_buffer)
        duration = len(audio) / SAMPLE_RATE
        log.debug("Processing %.1fs of audio", duration)

        # --- ASR ---
        self.status.emit("Transcribing...")
        try:
            source_text = asr.transcribe(audio, language=self.asr_language)
        except Exception as e:
            log.error("ASR error: %s", e, exc_info=True)
            self.status.emit("Listening...")
            return

        if self._stop_flag:
            return

        if not source_text:
            self.status.emit("Listening...")
            return

        # Prepend pending text from previous timeout
        if self._pending_text:
            log.info("Prepending pending text: %s", self._pending_text[:60])
            source_text = self._pending_text + " " + source_text
            self._pending_text = ""

        log.info("ASR: %s", source_text)
        self.transcribed.emit(source_text)

        # --- Translate to all target languages ---
        self.status.emit("Translating...")
        results = {}
        any_timeout = False
        for lang, translator in self._translators.items():
            if self._stop_flag:
                return
            try:
                result = translator.translate(source_text)
                if result:
                    results[lang] = result
            except TranslationTimeout:
                log.warning("Translation timeout for %s — will retry next round", lang)
                any_timeout = True
            except Exception as e:
                log.error("Translation error (%s): %s", lang, e, exc_info=True)

        if self._stop_flag:
            return

        # Save source text for retry if any translation timed out
        if any_timeout:
            self._pending_text = source_text
            # Safety cap to prevent unbounded growth
            if len(self._pending_text) > 500:
                self._pending_text = self._pending_text[-300:]

        if results:
            log.info("Translated: %s", results)
            self.translated.emit(results)

        self.status.emit("Listening...")

    def request_stop(self):
        """Non-blocking stop — sets flag. Returns immediately.

        NOTE: We intentionally do NOT close HTTP sessions here because
        request_stop() is called from the main thread, but the sessions
        are used by the pipeline thread. requests.Session is not thread-safe;
        closing from a different thread causes native crashes (segfault in
        urllib3/socket layer). Sessions are closed in the pipeline's finally
        block (same thread) instead.
        """
        self._stop_flag = True

    def stop(self):
        """Blocking stop — request_stop + short wait.  Used only by closeEvent."""
        self.request_stop()
        self.wait(5000)
