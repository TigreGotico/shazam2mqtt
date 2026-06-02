"""MQTT client wrapper with Home Assistant MQTT discovery."""

import json
import logging
from typing import Any

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


class MqttClient:
    """Wraps paho-mqtt with Home Assistant auto-discovery for multiple sensors."""

    def __init__(self, config):
        self.cfg = config
        self._client = mqtt.Client()
        if config.mqtt_user and config.mqtt_pass:
            self._client.username_pw_set(config.mqtt_user, config.mqtt_pass)

        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

        # Topics
        self._command_topic = f"shazam2mqtt/{config.device_name}/command"
        self._status_topic = f"shazam2mqtt/{config.device_name}/status"

        self._t_now_playing = f"shazam2mqtt/{config.device_name}/now_playing"
        self._t_now_playing_attrs = f"shazam2mqtt/{config.device_name}/now_playing/attributes"
        self._t_status_text = f"shazam2mqtt/{config.device_name}/status_text"
        self._t_matched = f"shazam2mqtt/{config.device_name}/matched"
        self._t_track = f"shazam2mqtt/{config.device_name}/track"
        self._t_artist = f"shazam2mqtt/{config.device_name}/artist"
        self._t_confidence = f"shazam2mqtt/{config.device_name}/confidence"
        self._t_url = f"shazam2mqtt/{config.device_name}/apple_music_url"
        self._t_artwork = f"shazam2mqtt/{config.device_name}/artwork_url"
        self._t_noise = f"shazam2mqtt/{config.device_name}/noise_level"

        self._listen_callback = None

    # ------------------------------------------------------------------ #
    # lifecycle
    # ------------------------------------------------------------------ #

    def connect(self) -> None:
        logger.info("Connecting to MQTT broker %s:%d …", self.cfg.mqtt_host, self.cfg.mqtt_port)
        self._client.will_set(self._status_topic, payload="offline", retain=True)
        self._client.connect(self.cfg.mqtt_host, self.cfg.mqtt_port, 60)
        self._client.loop_start()

    def disconnect(self) -> None:
        self.publish_availability("offline")
        self._client.loop_stop()
        self._client.disconnect()
        logger.info("MQTT disconnected")

    # ------------------------------------------------------------------ #
    # callbacks
    # ------------------------------------------------------------------ #

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("MQTT connected")
            self.publish_availability("online")
            if self.cfg.ha_enabled:
                self._send_discovery()
            client.subscribe(self._command_topic)
            logger.info("Subscribed to %s", self._command_topic)
        else:
            logger.error("MQTT connect failed (rc=%d)", rc)

    def _on_disconnect(self, client, userdata, rc):
        logger.warning("MQTT disconnected (rc=%d)", rc)

    def _on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode("utf-8", errors="ignore").strip().lower()
        logger.debug("MQTT message on %s: %s", topic, payload)
        if topic == self._command_topic and payload == "listen_now":
            if self._listen_callback:
                logger.info("Command 'listen_now' received")
                self._listen_callback()

    # ------------------------------------------------------------------ #
    # HA discovery
    # ------------------------------------------------------------------ #

    def _send_discovery(self):
        device = {
            "identifiers": [f"{self.cfg.device_name}_shazam"],
            "name": f"{self.cfg.device_name.replace('_', ' ').title()} Shazam",
            "model": "Shazam2MQTT",
            "manufacturer": "TigreGotico",
        }

        def _sensor(name: str, uid: str, topic: str, **extra) -> dict:
            return {
                "name": name,
                "state_topic": topic,
                "availability_topic": self._status_topic,
                "unique_id": f"{self.cfg.device_name}_shazam_{uid}",
                "device": device,
                **extra,
            }

        sensors = [
            (
                f"{self.cfg.ha_discovery_prefix}/sensor/{self.cfg.device_name}_shazam_now_playing/config",
                _sensor("Now Playing", "now_playing", self._t_now_playing, icon="mdi:music-note", json_attributes_topic=self._t_now_playing_attrs),
            ),
            (
                f"{self.cfg.ha_discovery_prefix}/sensor/{self.cfg.device_name}_shazam_status/config",
                _sensor("Status", "status", self._t_status_text, icon="mdi:information-outline"),
            ),
            (
                f"{self.cfg.ha_discovery_prefix}/sensor/{self.cfg.device_name}_shazam_track/config",
                _sensor("Track", "track", self._t_track, icon="mdi:album"),
            ),
            (
                f"{self.cfg.ha_discovery_prefix}/sensor/{self.cfg.device_name}_shazam_artist/config",
                _sensor("Artist", "artist", self._t_artist, icon="mdi:account-music"),
            ),
            (
                f"{self.cfg.ha_discovery_prefix}/sensor/{self.cfg.device_name}_shazam_confidence/config",
                _sensor(
                    "Confidence",
                    "confidence",
                    self._t_confidence,
                    icon="mdi:counter",
                    unit_of_measurement="matches",
                ),
            ),
            (
                f"{self.cfg.ha_discovery_prefix}/sensor/{self.cfg.device_name}_shazam_apple_music_url/config",
                _sensor("Apple Music URL", "apple_music_url", self._t_url, icon="mdi:link"),
            ),
            (
                f"{self.cfg.ha_discovery_prefix}/sensor/{self.cfg.device_name}_shazam_artwork_url/config",
                _sensor("Artwork URL", "artwork_url", self._t_artwork, icon="mdi:image"),
            ),
            (
                f"{self.cfg.ha_discovery_prefix}/sensor/{self.cfg.device_name}_shazam_noise_level/config",
                _sensor(
                    "Noise Level",
                    "noise_level",
                    self._t_noise,
                    icon="mdi:microphone",
                    unit_of_measurement="dBFS",
                ),
            ),
            # binary sensor
            (
                f"{self.cfg.ha_discovery_prefix}/binary_sensor/{self.cfg.device_name}_shazam_matched/config",
                {
                    "name": "Matched",
                    "state_topic": self._t_matched,
                    "availability_topic": self._status_topic,
                    "unique_id": f"{self.cfg.device_name}_shazam_matched",
                    "payload_on": "ON",
                    "payload_off": "OFF",
                    "device_class": "sound",
                    "device": device,
                },
            ),
        ]

        for topic, payload in sensors:
            self._client.publish(topic, payload=json.dumps(payload), retain=True)
            logger.info("Sent HA discovery to %s", topic)

    # ------------------------------------------------------------------ #
    # publishing helpers
    # ------------------------------------------------------------------ #

    def publish_availability(self, status: str):
        self._client.publish(self._status_topic, payload=status, retain=True)

    def _pub(self, topic: str, payload: str, retain: bool = False):
        self._client.publish(topic, payload=payload, retain=retain)

    # ------------------------------------------------------------------ #
    # state publishers
    # ------------------------------------------------------------------ #

    def publish_match(
        self,
        title: str,
        subtitle: str,
        confidence: int = 0,
        url: str = "",
        artwork_url: str = "",
    ):
        """Publish a successful match to all relevant topics."""
        self._pub(self._t_now_playing, f"{title} — {subtitle}")
        self._pub(
            self._t_now_playing_attrs,
            json.dumps(
                {
                    "artist": subtitle,
                    "title": title,
                    "confidence": confidence,
                    "apple_music_url": url or "Unknown",
                    "artwork_url": artwork_url or "Unknown",
                }
            ),
        )
        self._pub(self._t_status_text, "playing")
        self._pub(self._t_matched, "ON")
        self._pub(self._t_track, title)
        self._pub(self._t_artist, subtitle)
        self._pub(self._t_confidence, str(confidence))
        self._pub(self._t_url, url or "Unknown")
        self._pub(self._t_artwork, artwork_url or "Unknown")
        logger.info("Published match: %s — %s", title, subtitle)

    def publish_unknown(self, reason: str = "No match"):
        self._pub(self._t_now_playing, f"Unknown / {reason}")
        self._pub(self._t_now_playing_attrs, "{}")
        self._pub(self._t_status_text, "unknown")
        self._pub(self._t_matched, "OFF")
        self._pub(self._t_track, "Unknown")
        self._pub(self._t_artist, "Unknown")
        self._pub(self._t_confidence, "0")
        self._pub(self._t_url, "Unknown")
        self._pub(self._t_artwork, "Unknown")
        logger.info("Published unknown: %s", reason)

    def publish_silence(self):
        self._pub(self._t_now_playing, "Silence")
        self._pub(self._t_now_playing_attrs, "{}")
        self._pub(self._t_status_text, "silence")
        self._pub(self._t_matched, "OFF")
        self._pub(self._t_track, "-")
        self._pub(self._t_artist, "-")
        self._pub(self._t_confidence, "0")
        self._pub(self._t_url, "-")
        self._pub(self._t_artwork, "-")
        logger.info("Published silence")

    def publish_noise_level(self, dbfs: float):
        self._pub(self._t_noise, f"{dbfs:.1f}")

    # ------------------------------------------------------------------ #
    # command hook
    # ------------------------------------------------------------------ #

    def set_listen_callback(self, callback):
        self._listen_callback = callback
