"""Audio capture via sounddevice and RMS-based noise gate."""

import asyncio
import logging
import wave
from io import BytesIO
from typing import Callable

import numpy as np
import sounddevice as sd

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = np.int16
CHUNK_SECONDS = 1
CHUNK_SAMPLES = int(SAMPLE_RATE * CHUNK_SECONDS)


def rms_to_dbfs(rms: float) -> float:
    """Convert RMS amplitude to dBFS for int16 audio."""
    if rms <= 0:
        return -np.inf
    return 20 * np.log10(rms / 32768.0)


def compute_dbfs(chunk: np.ndarray) -> float:
    rms = np.sqrt(np.mean(chunk.astype(np.float64) ** 2))
    return rms_to_dbfs(rms)


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


class AudioCapture:
    """Capture fixed-duration audio from the default microphone."""

    def __init__(
        self,
        duration: int = 10,
        sample_rate: int = SAMPLE_RATE,
        channels: int = CHANNELS,
    ):
        self.duration = duration
        self.sample_rate = sample_rate
        self.channels = channels

    def capture(self) -> bytes:
        """Record and return raw int16 mono bytes (not WAV wrapped)."""
        logger.info("Capturing %d s of audio …", self.duration)
        frames = self.duration * self.sample_rate
        recording = sd.rec(
            frames,
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype=DTYPE,
            blocking=True,
        )
        return recording.tobytes()

    def capture_to_wav(self) -> bytes:
        """Capture and return a complete in-memory WAV file."""
        raw = self.capture()
        buf = BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # int16 = 2 bytes
            wf.setframerate(self.sample_rate)
            wf.writeframes(raw)
        return buf.getvalue()

    async def capture_to_wav_async(self) -> bytes:
        """Async wrapper that offloads blocking capture to a thread."""
        return await asyncio.to_thread(self.capture_to_wav)


class AudioMonitor:
    """Continuously monitors the mic and yields trigger events + noise levels.

    When the noise gate fires, this class captures a full clip and passes
    it to the async ``on_trigger`` callback.  There is only *one* ``sd.rec``
    call active at any moment, so PortAudio contention is avoided.
    """

    def __init__(
        self,
        noise_gate_db: float = -40.0,
        hysteresis_chunks: int = 3,
        capture_duration: int = 10,
    ):
        self.gate = NoiseGate(noise_gate_db, hysteresis_chunks)
        self.capture = AudioCapture(duration=capture_duration)

    async def run(
        self,
        on_trigger: Callable[[bytes], None],
        on_noise_level: Callable[[float], None] | None = None,
    ) -> None:
        logger.info(
            "Audio monitor started (threshold=%.1f dBFS, hysteresis=%d s)",
            self.gate.threshold_db,
            self.gate.hysteresis_chunks,
        )
        while True:
            try:
                chunk = await asyncio.to_thread(
                    sd.rec,
                    CHUNK_SAMPLES,
                    samplerate=SAMPLE_RATE,
                    channels=CHANNELS,
                    dtype=DTYPE,
                    blocking=True,
                )
                db = compute_dbfs(chunk)
                if on_noise_level is not None:
                    on_noise_level(db)
                if self.gate.process(chunk):
                    logger.info("Noise gate triggered (%.1f dBFS)", db)
                    wav = await self.capture.capture_to_wav_async()
                    await on_trigger(wav)
                    await asyncio.sleep(1)
                    self.gate.reset()
            except sd.PortAudioError as exc:
                logger.error("PortAudio error: %s", exc)
                await asyncio.sleep(5)
            except Exception as exc:
                logger.exception("Unexpected error in audio monitor: %s", exc)
                await asyncio.sleep(1)
