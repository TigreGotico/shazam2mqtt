"""Thin async wrapper around shazampy for byte-array identification."""

import asyncio
import logging

from shazampy import ShazamClient, ShazamTransport, RecognitionResult

logger = logging.getLogger(__name__)


class ShazamBridge:
    """Wraps shazampy so the state machine never holds a transport session open."""

    async def identify(self, wav_bytes: bytes) -> RecognitionResult:
        """Identify audio from WAV bytes. Returns a typed RecognitionResult."""
        async with ShazamTransport() as transport:
            client = ShazamClient(transport)
            return await client.identify(wav_bytes)

    async def get_track_info(self, track_id: str) -> "Track":
        """Fetch extended track metadata (lyrics, videos, sections)."""
        from shazampy import Track
        async with ShazamTransport() as transport:
            client = ShazamClient(transport)
            return await client.get_track_info(track_id)
