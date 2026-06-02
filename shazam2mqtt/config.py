"""Environment-based configuration with sensible defaults."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    device_name: str
    mqtt_host: str
    mqtt_port: int
    mqtt_user: str | None
    mqtt_pass: str | None
    noise_gate_db: float
    listen_duration: int
    cooldown_seconds: int
    same_song_cooldown_seconds: int
    ha_discovery_prefix: str
    ha_enabled: bool
    sample_rate: int

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            device_name=os.getenv("DEVICE_NAME", "shazam"),
            mqtt_host=os.getenv("MQTT_HOST", "localhost"),
            mqtt_port=int(os.getenv("MQTT_PORT", "1883")),
            mqtt_user=os.getenv("MQTT_USER") or None,
            mqtt_pass=os.getenv("MQTT_PASS") or None,
            noise_gate_db=float(os.getenv("NOISE_GATE_DB", "-40")),
            listen_duration=int(os.getenv("LISTEN_DURATION", "10")),
            cooldown_seconds=int(os.getenv("COOLDOWN_SECONDS", "60")),
            same_song_cooldown_seconds=int(os.getenv("SAME_SONG_COOLDOWN_SECONDS", "300")),
            ha_discovery_prefix=os.getenv("HA_DISCOVERY_PREFIX", "homeassistant"),
            ha_enabled=os.getenv("HA_ENABLED", "true").lower() in ("1", "true", "yes"),
            sample_rate=int(os.getenv("SAMPLE_RATE", "44100")),
        )
