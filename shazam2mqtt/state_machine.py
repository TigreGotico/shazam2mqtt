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
        if not self._cooldown_elapsed():
            remaining = self.cfg.cooldown_seconds - (time.time() - self._last_trigger)
            logger.debug("Cooldown active (%.1f s left), ignoring trigger", remaining)
            return

        self._busy = True
        self._last_trigger = time.time()
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

        matches = result.get("matches", [])
        track = result.get("track", {})
        title = track.get("title", "")
        subtitle = track.get("subtitle", "")
        track_key = f"{title}::{subtitle}".lower()

        if matches and title:
            logger.info("Shazam match: %s — %s (%d matches)", title, subtitle, len(matches))
            self._publish_match(title, subtitle, track, len(matches))
        else:
            logger.info("Shazam returned no match")
            self.mqtt.publish_unknown("No match")

        # same-song cooldown extension
        if track_key and track_key == self._last_track:
            extra = self.cfg.same_song_cooldown_seconds - self.cfg.cooldown_seconds
            if extra > 0:
                logger.info("Same song detected, extending cooldown by %d s", extra)
                self._last_trigger = time.time() + extra
        self._last_track = track_key

    def _publish_match(self, title: str, subtitle: str, track: dict, match_count: int):
        url = ""
        hub = track.get("hub", {})
        actions = hub.get("actions", [])
        for action in actions:
            if action.get("type") == "applemusicopen":
                url = action.get("uri", "")
                break
        artwork = track.get("images", {}).get("coverart", "")
        self.mqtt.publish_match(
            title, subtitle, confidence=match_count, url=url, artwork_url=artwork
        )

    # ------------------------------------------------------------------ #
    # cooldown helpers
    # ------------------------------------------------------------------ #

    def _cooldown_elapsed(self) -> bool:
        return time.time() - self._last_trigger >= self.cfg.cooldown_seconds
