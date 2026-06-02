# Docker Reference

## Build locally

```bash
cd apps/shazam2mqtt
docker build -t shazam2mqtt .
```

For a private `xazam` dependency, pass a GitHub token:

```bash
docker build --build-arg GITHUB_TOKEN=$GH_TOKEN -t shazam2mqtt .
```

## Docker Compose

A `docker-compose.yml` is included. Create a `.env` file:

```bash
DEVICE_NAME=living_room
MQTT_HOST=192.168.1.200
MQTT_USER=mqtt
MQTT_PASS=secret
NOISE_GATE_DB=-40
```

Then run:

```bash
docker compose up -d
```

## Audio backends

### ALSA (default)

The compose file passes `/dev/snd` into the container.

### PulseAudio / PipeWire

Comment out the `devices:` block and uncomment the `volumes:` / `PULSE_SERVER` lines in `docker-compose.yml`.

## Tags

| Tag | Source |
|-----|--------|
| `dev` | latest push to `dev` branch |
| `vX.Y.Z` | git tag |

All images are published to `ghcr.io/tigregotico/shazam2mqtt`.
