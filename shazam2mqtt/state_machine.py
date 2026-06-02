"""State machine: listens for audio triggers, calls Shazam, publishes to MQTT."""

import asyncio
import logging
import time

from shazam2mqtt.mqtt_client import MqttClient
from shazam2mqtt.shazam_client import ShazamBridge

logger = logging.getLogger(__name__)


class ShazamStateMachine:
    """Orchestrates the identify-publish loop with a simple cooldown guard."""

    def __init__(self, config, mqtt: MqttClient):
        self.cfg = config
        self.mqtt = mqtt
        self.shazam = ShazamBridge()

        self._last_trigger = 0.0
        self._last_track = ""
        self._busy = False

        # Register the command callback so HA can trigger a listen
        self.mqtt.set_listen_callback(self._on_listen_command)

    # ------------------------------------------------------------------ #
    # public API
    # ------------------------------------------------------------------ #

    async def on_trigger(self, wav_bytes: bytes) -> None:
        """Called by the audio monitor when the noise gate fires."""
        if self._busy:
            logger.debug("Already busy, ignoring trigger")
            return

        elapsed = time.time() - self._last_trigger
        active_cooldown = self._active_cooldown()
        if elapsed < active_cooldown:
            remaining = active_cooldown - elapsed
            logger.debug(
                "Cooldown active (%.1f s left, mode=%s)",
                remaining,
                "same-song" if self._same_song_flag else "normal",
            )
            return

        self._busy = True
        self._last_trigger = time.time()
        # Reset same-song flag; will be set again if this trigger yields the same track
        self._same_song_flag = False
        try:
            await self._identify_and_publish(wav_bytes)
        finally:
            self._busy = False

    # ------------------------------------------------------------------ #
    # command handler
    # ------------------------------------------------------------------ #

    def _on_listen_command(self):
        """MQTT command received — schedule an async listen."""
        # We can't capture audio from the MQTT thread, but we can set a flag
        # that the monitor checks on its next loop.  For now we just log;
        # a full implementation would signal the monitor to force-capture.
        logger.info("Command 'listen_now' received (not yet wired to forced capture)")

    # ------------------------------------------------------------------ #
    # core cycle
    # ------------------------------------------------------------------ #

    async def _identify_and_publish(self, wav_bytes: bytes):
        try:
            result = await self.shazam.identify(wav_bytes)
        except Exception as exc:
            logger.exception("Shazam identification failed: %s", exc)
            self.mqtt.publish_unknown("Identification error")
            return

        if not result.matched or not result.track:
            logger.info("Shazam returned no match")
            self.mqtt.publish_unknown("No match")
            return

        track = result.track
        title = track.title
        subtitle = track.subtitle
        track_key = f"{title}::{subtitle}".lower()

        logger.info(
            "Shazam match: %s — %s (%d matches)",
            title, subtitle, track.confidence,
        )

        # Try to enrich with extra metadata (lyrics, videos, sections)
        try:
            extra = await self.shazam.get_track_info(track.key)
        except Exception as exc:
            logger.warning("Could not fetch extra track info: %s", exc)
            extra = None

        self._publish_match(track, extra)

        # Same-song cooldown
        if track_key and track_key == self._last_track:
            self._same_song_flag = True
            logger.info(
                "Same song detected — next cooldown will be %d s",
                self.cfg.same_song_cooldown_seconds,
            )
        else:
            self._same_song_flag = False
        self._last_track = track_key

    def _publish_match(self, track, extra_track=None):
        """Publish a match using the rich typed Track model."""
        # Prefer extra track data if available (has lyrics, videos, sections)
        source = extra_track if extra_track else track
        self.mqtt.publish_match(
            title=track.title,
            subtitle=track.subtitle,
            confidence=track.confidence,
            url=track.apple_music_url,
            artwork_url=track.cover_art,
            lyrics=source.lyrics,
            genres=track.genres,
            spotify_url=track.spotify_uri,
            deezer_url=track.deezer_uri,
            shazam_url=track.url,
            metadata=source.metadata_table,
            related_videos=source.related_videos,
        )

    # ------------------------------------------------------------------ #
    # cooldown helpers
    # ------------------------------------------------------------------ #

    def _active_cooldown(self) -> int:
        """Return the cooldown duration that currently applies."""
        if getattr(self, "_same_song_flag", False):
            return self.cfg.same_song_cooldown_seconds
        return self.cfg.cooldown_seconds
