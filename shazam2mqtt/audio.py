"""Audio capture via sounddevice and RMS-based noise gate."""

import asyncio
import logging
import time
import wave
from io import BytesIO
from typing import Callable

import numpy as np
import sounddevice as sd

logger = logging.getLogger(__name__)

CHANNELS = 1
DTYPE = np.int16
CHUNK_SECONDS = 1
DEFAULT_SAMPLE_RATE = 44100


def rms_to_dbfs(rms: float) -> float:
    """Convert RMS amplitude to dBFS for int16 audio."""
    if rms <= 0:
        return -np.inf
    return 20 * np.log10(rms / 32768.0)


def compute_dbfs(chunk: np.ndarray) -> float:
    rms = np.sqrt(np.mean(chunk.astype(np.float64) ** 2))
    return rms_to_dbfs(rms)


def list_input_devices() -> str:
    """Return a human-readable list of available input devices."""
    try:
        devices = sd.query_devices()
        lines = ["Available audio devices:"]
        for i, dev in enumerate(devices):
            if dev["max_input_channels"] > 0:
                default_marker = " (DEFAULT)" if i == sd.default.device[0] else ""
                lines.append(
                    f"  [{i}] {dev['name']} — "
                    f"{dev['max_input_channels']} ch @ {int(dev['default_samplerate'])} Hz"
                    f"{default_marker}"
                )
        return "\n".join(lines)
    except Exception as exc:
        return f"Could not list audio devices: {exc}"


class NoiseGate:
    """Monitors incoming audio and triggers capture when loud enough."""

    def __init__(self, threshold_db: float, hysteresis_chunks: int = 3):
        self.threshold_db = threshold_db
        self.hysteresis_chunks = hysteresis_chunks
        self._loud_streak = 0

    def process(self, chunk: np.ndarray) -> bool:
        rms = np.sqrt(np.mean(chunk.astype(np.float64) ** 2))
        db = rms_to_dbfs(rms)
        if db > self.threshold_db:
            self._loud_streak += 1
        else:
            self._loud_streak = 0
        return self._loud_streak >= self.hysteresis_chunks

    def reset(self):
        self._loud_streak = 0


def wrap_wav(raw: bytes, sample_rate: int, channels: int = CHANNELS) -> bytes:
    """Wrap raw int16 PCM bytes into a complete in-memory WAV file."""
    buf = BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)  # int16 = 2 bytes
        wf.setframerate(sample_rate)
        wf.writeframes(raw)
    return buf.getvalue()


class NoiseLevelThrottler:
    """Throttle noise-level MQTT publishes: only emit when the value
    changes significantly or enough time has passed.
    """

    def __init__(
        self,
        callback: Callable[[float], None],
        min_interval: float = 5.0,
        min_delta: float = 3.0,
    ):
        self.callback = callback
        self.min_interval = min_interval
        self.min_delta = min_delta
        self._last_db: float | None = None
        self._last_time = 0.0

    def maybe_publish(self, db: float) -> None:
        now = time.time()
        elapsed = now - self._last_time
        delta = abs(db - self._last_db) if self._last_db is not None else float("inf")

        if elapsed >= self.min_interval or delta >= self.min_delta:
            self.callback(db)
            self._last_db = db
            self._last_time = now


class AudioMonitor:
    """Continuously monitors the mic and yields trigger events + noise levels.

    When the noise gate fires, this class captures a full clip and passes
    it to the async ``on_trigger`` callback.  When the room has been quiet
    for ``quiet_hysteresis`` consecutive chunks, it calls ``on_quiet``.
    """

    def __init__(
        self,
        noise_gate_db: float = -40.0,
        hysteresis_chunks: int = 3,
        capture_duration: int = 10,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        device: int | None = None,
        noise_level_interval: float = 5.0,
        noise_level_delta: float = 3.0,
        quiet_hysteresis: int = 5,
    ):
        self.gate = NoiseGate(noise_gate_db, hysteresis_chunks)
        self.capture_duration = capture_duration
        self.sample_rate = sample_rate
        self.device = device
        self.noise_level_interval = noise_level_interval
        self.noise_level_delta = noise_level_delta
        self.quiet_hysteresis = quiet_hysteresis
        self._chunk_samples = int(sample_rate * CHUNK_SECONDS)
        self._quiet_streak = 0

    def _open_stream(self) -> sd.InputStream:
        kwargs = {
            "samplerate": self.sample_rate,
            "channels": CHANNELS,
            "dtype": DTYPE,
            "blocksize": self._chunk_samples,
        }
        if self.device is not None:
            kwargs["device"] = self.device
        stream = sd.InputStream(**kwargs)
        stream.start()
        return stream

    async def _capture_clip(self, stream: sd.InputStream) -> bytes:
        """Read a full capture-duration clip from the already-open stream."""
        frames = self.capture_duration * self.sample_rate
        data, overflowed = await asyncio.to_thread(stream.read, frames)
        if overflowed:
            logger.debug("Input overflow while capturing clip")
        return wrap_wav(data.tobytes(), self.sample_rate)

    async def run(
        self,
        on_trigger: Callable[[bytes], None],
        on_noise_level: Callable[[float], None] | None = None,
        on_quiet: Callable[[], None] | None = None,
        force_listen: asyncio.Event | None = None,
    ) -> None:
        logger.info(list_input_devices())
        logger.info(
            "Audio monitor started (threshold=%.1f dBFS, hysteresis=%d s, "
            "sample_rate=%d Hz, device=%s, quiet_hysteresis=%d s)",
            self.gate.threshold_db,
            self.gate.hysteresis_chunks,
            self.sample_rate,
            self.device if self.device is not None else "default",
            self.quiet_hysteresis,
        )

        throttler = (
            NoiseLevelThrottler(
                on_noise_level,
                min_interval=self.noise_level_interval,
                min_delta=self.noise_level_delta,
            )
            if on_noise_level
            else None
        )

        stream: sd.InputStream | None = None
        try:
            while True:
                try:
                    if stream is None:
                        stream = self._open_stream()

                    if force_listen is not None and force_listen.is_set():
                        force_listen.clear()
                        logger.info("Forced listen requested — capturing now")
                        wav = await self._capture_clip(stream)
                        await on_trigger(wav)
                        self._quiet_streak = 0
                        self.gate.reset()
                        continue

                    data, overflowed = await asyncio.to_thread(stream.read, self._chunk_samples)
                    if overflowed:
                        logger.debug("Input overflow while monitoring")
                    chunk = data
                    db = compute_dbfs(chunk)
                    logger.debug("Noise level: %.1f dBFS", db)

                    if throttler is not None:
                        throttler.maybe_publish(db)

                    triggered = self.gate.process(chunk)
                    if triggered:
                        self._quiet_streak = 0
                        logger.info("Noise gate triggered (%.1f dBFS)", db)
                        wav = await self._capture_clip(stream)
                        await on_trigger(wav)
                        await asyncio.sleep(1)
                        self.gate.reset()
                    else:
                        self._quiet_streak += 1
                        if on_quiet and self._quiet_streak >= self.quiet_hysteresis:
                            logger.info("Room quiet for %d s", self.quiet_hysteresis)
                            await on_quiet()
                            self._quiet_streak = 0
                except sd.PortAudioError as exc:
                    logger.error("PortAudio error: %s — reopening stream in 5s", exc)
                    if stream is not None:
                        try:
                            stream.close()
                        except Exception:
                            pass
                        stream = None
                    await asyncio.sleep(5)
                except Exception as exc:
                    logger.exception("Unexpected error in audio monitor: %s", exc)
                    await asyncio.sleep(1)
        finally:
            if stream is not None:
                try:
                    stream.close()
                except Exception:
                    pass
