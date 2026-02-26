"""Audio device listing and capture (PyAudioWPatch for WASAPI loopback support)."""

import logging
import threading
import time
import numpy as np

log = logging.getLogger(__name__)

try:
    import pyaudiowpatch as pyaudio
except ImportError:
    import pyaudio  # fallback — no loopback support

from config import SAMPLE_RATE, CHANNELS

# Prevent immediate garbage collection of PortAudio instances.
# pa.terminate() can segfault when PyQt6 is still active (both fight
# over native resources).  Stashing here keeps them alive until process
# exit, where the OS handles cleanup safely.
_deferred_pa = []


def list_audio_devices():
    """Return list of (index, name) for input + loopback devices.

    Input devices (microphones) are prefixed with 🎤.
    Output devices (speakers/headphones) are listed as loopback with 🔊.
    """
    p = pyaudio.PyAudio()
    results = []

    try:
        # Find WASAPI host API
        wasapi_idx = None
        for i in range(p.get_host_api_count()):
            api = p.get_host_api_info_by_index(i)
            if "WASAPI" in api.get("name", ""):
                wasapi_idx = i
                break

        if wasapi_idx is None:
            # No WASAPI — list all input devices
            for i in range(p.get_device_count()):
                dev = p.get_device_info_by_index(i)
                if dev["maxInputChannels"] > 0:
                    results.append((i, dev["name"]))
            return results

        seen_indices = set()

        # WASAPI input devices (microphones, stereo mix, etc.)
        for i in range(p.get_device_count()):
            dev = p.get_device_info_by_index(i)
            if dev["hostApi"] == wasapi_idx and dev["maxInputChannels"] > 0:
                is_lb = "loopback" in dev["name"].lower()
                prefix = "\U0001f50a" if is_lb else "\U0001f3a4"
                results.append((i, f"{prefix} {dev['name']}"))
                seen_indices.add(i)
                log.debug("Input device %d: %s (ch=%d, rate=%.0f)",
                          i, dev["name"], dev["maxInputChannels"],
                          dev["defaultSampleRate"])

        # WASAPI output devices — get loopback versions (PyAudioWPatch only)
        if hasattr(p, "get_loopback_device_info_for_device"):
            for i in range(p.get_device_count()):
                dev = p.get_device_info_by_index(i)
                if (dev["hostApi"] == wasapi_idx
                        and dev["maxOutputChannels"] > 0
                        and dev["maxInputChannels"] == 0):
                    try:
                        lb = p.get_loopback_device_info_for_device(dev)
                        if lb["index"] not in seen_indices:
                            results.append(
                                (lb["index"], f"\U0001f50a {dev['name']} (Loopback)")
                            )
                            seen_indices.add(lb["index"])
                            log.debug("Loopback device %d for output %d: %s",
                                      lb["index"], i, dev["name"])
                    except Exception:
                        pass
    finally:
        p.terminate()

    if not results:
        # Ultimate fallback: any input device
        p2 = pyaudio.PyAudio()
        try:
            for i in range(p2.get_device_count()):
                dev = p2.get_device_info_by_index(i)
                if dev["maxInputChannels"] > 0:
                    results.append((i, dev["name"]))
        finally:
            p2.terminate()

    return results


# Backward-compatible alias
list_loopback_devices = list_audio_devices


def get_device_samplerate(device_index: int) -> int:
    """Get the native sample rate of a device."""
    p = pyaudio.PyAudio()
    try:
        info = p.get_device_info_by_index(device_index)
        return int(info["defaultSampleRate"])
    finally:
        p.terminate()


class AudioCapture:
    """Captures audio via WASAPI and pushes 16kHz mono chunks to a queue."""

    def __init__(self, device_index: int, audio_queue, target_rate=SAMPLE_RATE):
        self.device_index = device_index
        self.audio_queue = audio_queue
        self.target_rate = target_rate
        self._stream = None
        self._pa = None
        self._running = False
        self._thread = None
        self._started_event = threading.Event()
        self._start_error = None

        # Get device info
        self._pa = pyaudio.PyAudio()
        dev = self._pa.get_device_info_by_index(device_index)
        self._native_rate = int(dev["defaultSampleRate"])
        self._channels = max(dev["maxInputChannels"], 1)
        log.info("Device %d: %s, rate=%d, ch=%d",
                 device_index, dev["name"], self._native_rate, self._channels)

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

    def _audio_callback(self, in_data, frame_count, time_info, status):
        """PortAudio callback — runs in a native audio thread."""
        if not self._running:
            return (None, pyaudio.paComplete)

        try:
            chunk = np.frombuffer(in_data, dtype=np.float32)

            # Multi-channel → mono
            if self._channels > 1:
                chunk = chunk.reshape(-1, self._channels).mean(axis=1)

            # Resample to target rate if needed
            if self._native_rate != self.target_rate:
                ratio = self.target_rate / self._native_rate
                new_len = int(len(chunk) * ratio)
                if new_len > 0:
                    indices = np.linspace(0, len(chunk) - 1, new_len).astype(int)
                    chunk = chunk[indices]

            self.audio_queue.put(("audio", chunk))
        except Exception as e:
            self.audio_queue.put(("error", str(e)))

        return (None, pyaudio.paContinue)

    def _run(self):
        try:
            blocksize = int(self._native_rate * 0.03)  # 30ms at native rate
            log.info("Opening audio stream: device=%d rate=%d blocksize=%d ch=%d",
                     self.device_index, self._native_rate, blocksize, self._channels)

            self._stream = self._pa.open(
                format=pyaudio.paFloat32,
                channels=self._channels,
                rate=self._native_rate,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=blocksize,
                stream_callback=self._audio_callback,
            )
            self._stream.start_stream()
            log.info("Audio stream started successfully")
            self._started_event.set()

            # Sleep loop — non-blocking, exits quickly when _running is False
            while self._running and self._stream.is_active():
                time.sleep(0.1)

        except Exception as e:
            log.error("Audio capture error: %s", e, exc_info=True)
            self._start_error = str(e)
            self._started_event.set()  # unblock the caller
            self.audio_queue.put(("error", str(e)))
        finally:
            if self._stream is not None:
                try:
                    self._stream.stop_stream()
                    self._stream.close()
                except Exception:
                    pass
                self._stream = None

    def stop(self):
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=3)
            self._thread = None
        # Defer pa.terminate() — calling it while PyQt6 is active can
        # segfault (same native-resource conflict as CUDA models).
        if self._pa is not None:
            _deferred_pa.append(self._pa)
            self._pa = None
        log.info("Audio capture stopped")
