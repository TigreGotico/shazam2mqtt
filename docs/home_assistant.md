# Home Assistant Integration

## Auto-discovery

When `HA_ENABLED=true`, shazam2mqtt publishes MQTT discovery configs on startup. Home Assistant automatically creates a device with 7 sensors and 1 binary sensor under **Settings → Devices & Services → MQTT**.

## Entities

| Entity | Type | Example state |
|--------|------|--------------|
| `<name> Shazam Now Playing` | sensor | `Nothing Else Matters - Metallica` |
| `<name> Shazam Status` | sensor | `playing` / `unknown` / `silence` |
| `<name> Shazam Matched` | binary_sensor | `ON` / `OFF` |
| `<name> Shazam Track` | sensor | `Nothing Else Matters` |
| `<name> Shazam Artist` | sensor | `Metallica` |
| `<name> Shazam Confidence` | sensor | `4` |
| `<name> Shazam Apple Music URL` | sensor | `https://music.apple.com/...` |
| `<name> Shazam Noise Level` | sensor | `-40.0` dBFS |

## Dashboard card (Markdown)

```yaml
type: markdown
content: >
  {% if is_state('sensor.living_room_shazam_status', 'playing') %}
    **Now Playing:** {{ states('sensor.living_room_shazam_now_playing') }}
  {% elif is_state('sensor.living_room_shazam_status', 'unknown') %}
    Unknown / No match
  {% else %}
    Silence
  {% endif %}
```

## Manual trigger

Publish `listen_now` to `shazam2mqtt/<name>/command` to force a capture on demand.

---
[← Docker](docker.md) · [Home](README.md) · [Lovelace →](lovelace.md)
