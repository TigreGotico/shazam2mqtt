"""Thin async wrapper around pyshazam for byte-array identification."""

import asyncio
import logging

from pyshazam import ShazamClient, ShazamTransport

logger = logging.getLogger(__name__)


class ShazamBridge:
    """Wraps pyshazam so the state machine never holds a transport session open."""

    async def identify(self, wav_bytes: bytes) -> dict:
        """Identify audio from WAV bytes. Returns the raw Shazam JSON dict."""
        async with ShazamTransport() as transport:
            client = ShazamClient(transport)
            return await client.identify_track(wav_bytes)
