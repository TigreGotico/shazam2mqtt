# Configuration

All settings are environment variables. There is no config file.

## Required

| Variable | Default | Description |
|----------|---------|-------------|
| `DEVICE_NAME` | `shazam` | Prefix for Home Assistant entity IDs. |
| `MQTT_HOST` | `localhost` | MQTT broker host. |
| `MQTT_PORT` | `1883` | MQTT broker port. |

## Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `MQTT_USER` | *(none)* | MQTT username. |
| `MQTT_PASS` | *(none)* | MQTT password. |
| `NOISE_GATE_DB` | `-40` | dBFS threshold. Audio quieter than this counts as silence. |
| `LISTEN_DURATION` | `10` | Seconds of audio to capture for Shazam. |
| `COOLDOWN_SECONDS` | `60` | Minimum seconds between captures. |
| `SAME_SONG_COOLDOWN_SECONDS` | `300` | Extra cooldown when the same song repeats. |
| `HA_DISCOVERY_PREFIX` | `homeassistant` | HA MQTT discovery prefix. |
| `HA_ENABLED` | `true` | Set to `false` to disable HA discovery. |

## Tuning the noise gate

- **Quiet room, speaker close to mic:** `-40` dBFS works well.
- **Noisy room or distant speaker:** try `-35` or `-30`.
- **False triggers:** lower the value (for example `-50`), or check that the mic is not picking up fan noise.

## Hysteresis

The gate requires 3 consecutive loud seconds before it triggers. This value is hard-coded to avoid reacting to single pops or keyboard clicks.

---
[Home](README.md) · [Docker →](docker.md)
