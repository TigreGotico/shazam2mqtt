# Docker Reference

## Pre-built image (recommended)

Images are published to GitHub Container Registry on every push to `dev` and every release tag:

```bash
docker pull ghcr.io/tigregotico/shazam2mqtt:dev
```

The `docker-compose.yml` in this repo uses the pre-built image by default. No local build is required.

## Build locally (if needed)

```bash
cd apps/shazam2mqtt
docker build -t shazam2mqtt .
```

The Dockerfile installs `xazam` from PyPI, so no GitHub token is needed.

## Docker Compose

A `docker-compose.yml` file is included. Create a `.env` file:

```bash
DEVICE_NAME=living_room
MQTT_HOST=192.168.1.200
MQTT_USER=mqtt
MQTT_PASS=secret
NOISE_GATE_DB=-40
LISTEN_DURATION=10
COOLDOWN_SECONDS=10
SAME_SONG_COOLDOWN_SECONDS=30
SAMPLE_RATE=44100
```

Then run:

```bash
docker compose pull
docker compose up -d
```

## Audio backends

### ALSA (default)

The compose file passes `/dev/snd` into the container.

### PipeWire

PipeWire exposes an ALSA compatibility layer, so `/dev/snd` still works. To force a specific capture device (for example a webcam mic), set the ALSA card name:

```bash
# Find the card name on the host
arecord -l
# Example output: card 3: C615 [HD Webcam C615]

# .env
ALSA_CARD=C615
```

### PulseAudio (legacy)

Comment out the `devices:` block and uncomment the `volumes:` / `PULSE_SERVER` lines in `docker-compose.yml`.

## Tags

| Tag | Source |
|-----|--------|
| `dev` | latest push to the `dev` branch |
| `vX.Y.Z` | git tag |

All images are published to `ghcr.io/tigregotico/shazam2mqtt`.

---
[← Configuration](configuration.md) · [Home](README.md) · [Home Assistant →](home_assistant.md)
