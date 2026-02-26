"""WASAPI loopback audio capture via sounddevice."""

import logging
import threading
import time
import numpy as np
import sounddevice as sd

from config import SAMPLE_RATE, CHANNELS

log = logging.getLogger(__name__)


def list_loopback_devices():
    """Return list of (index, name) for WASAPI loopback devices."""
    devices = sd.query_devices()
    hostapis = sd.query_hostapis()

    wasapi_idx = None
    for i, api in enumerate(hostapis):
        if "WASAPI" in api["name"]:
            wasapi_idx = i
            break

    results = []
    if wasapi_idx is not None:
        for idx, dev in enumerate(devices):
            if dev["hostapi"] == wasapi_idx and dev["max_input_channels"] > 0:
                results.append((idx, dev["name"]))
                log.debug("WASAPI device %d: %s (in=%d, rate=%.0f)",
                          idx, dev["name"], dev["max_input_channels"],
                          dev["default_samplerate"])

    if not results:
        # Fallback: all input-capable devices
        for idx, dev in enumerate(devices):
            if dev["max_input_channels"] > 0:
                results.append((idx, dev["name"]))

    return results


def get_device_samplerate(device_index: int) -> int:
    """Get the native sample rate of a device."""
    info = sd.query_devices(device_index)
    return int(info["default_samplerate"])


class AudioCapture:
    """Captures system audio via WASAPI loopback and pushes 16kHz mono chunks to a queue."""

    def __init__(self, device_index: int, audio_queue, target_rate=SAMPLE_RATE):
        self.device_index = device_index
        self.audio_queue = audio_queue
        self.target_rate = target_rate
        self._stream = None
        self._running = False
        self._thread = None
        self._started_event = threading.Event()
        self._start_error = None

        # Get native rate — resample if needed
        self._native_rate = get_device_samplerate(device_index)
        log.info("Device %d native rate: %d, target: %d",
                 device_index, self._native_rate, target_rate)

    def start(self):
        """Start capture. Blocks up to 5s to confirm stream is actually running.
        Raises RuntimeError on failure."""
        if self._running:
            return
        self._running = True
        self._started_event.clear()
        self._start_error = None
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

        # Wait for the stream to actually start (or fail)
        if not self._started_event.wait(timeout=5.0):
            self._running = False
            raise RuntimeError("Audio stream failed to start within 5 seconds")
        if self._start_error:
            self._running = False
            raise RuntimeError(self._start_error)

    def _run(self):
        try:
            blocksize = int(self._native_rate * 0.03)  # 30ms at native rate
            log.info("Opening audio stream: device=%d rate=%d blocksize=%d",
                     self.device_index, self._native_rate, blocksize)

            self._stream = sd.InputStream(
                samplerate=self._native_rate,
                blocksize=blocksize,
                device=self.device_index,
                channels=CHANNELS,
                dtype="float32",
                callback=self._audio_callback,
            )
            self._stream.start()
            log.info("Audio stream started successfully")
            self._started_event.set()

            while self._running:
                sd.sleep(100)

        except Exception as e:
            log.error("Audio capture error: %s", e, exc_info=True)
            self._start_error = str(e)
            self._started_event.set()  # unblock the caller
            self.audio_queue.put(("error", str(e)))
        finally:
            if self._stream is not None:
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception:
                    pass
                self._stream = None

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            log.debug("Audio status: %s", status)
        chunk = indata[:, 0].copy()  # mono float32

        # Resample to target rate if needed
        if self._native_rate != self.target_rate:
            ratio = self.target_rate / self._native_rate
            new_len = int(len(chunk) * ratio)
            if new_len > 0:
                indices = np.linspace(0, len(chunk) - 1, new_len).astype(int)
                chunk = chunk[indices]

        self.audio_queue.put(("audio", chunk))

    def stop(self):
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=3)
            self._thread = None
        log.info("Audio capture stopped")
