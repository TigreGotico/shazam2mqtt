#!/usr/bin/env python3
"""mic_recording.py — standalone test that records 5 seconds from the mic."""

import asyncio
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
CHANNELS = 1
DURATION = 5


def record_sync(path: str) -> None:
    print(f"Recording {DURATION} seconds from default mic …")
    recording = sd.rec(
        int(DURATION * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype=np.int16,
        blocking=True,
    )
    print(f"Done. RMS={np.sqrt(np.mean(recording.astype(np.float64)**2)):.1f}")
    with wave.open(path, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(recording.tobytes())
    print(f"Saved to {path}")


async def record_async(path: str) -> None:
    """Same as above but wrapped in asyncio.to_thread (matches shazam2mqtt)."""
    await asyncio.to_thread(record_sync, path)


async def main():
    out = Path("/tmp/mic_test.wav")
    await record_async(str(out))

    # Optional: quick Shazam test
    try:
        from shazam2mqtt.shazam_client import ShazamBridge
        bridge = ShazamBridge()
        result = await bridge.identify(out.read_bytes())
        track = result.get("track", {})
        if track:
            print(f"Shazam: {track.get('title')} — {track.get('subtitle')}")
        else:
            print("Shazam: no match")
    except Exception as exc:
        print(f"Shazam test failed: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
