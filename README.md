# shazam2mqtt

> **Because vinyl, tapes, and CDs don't have an API.**

`shazam2mqtt` is a Dockerised bridge that listens to your room, recognises whatever music is playing via Shazam, and publishes the result to MQTT — including Home Assistant auto-discovery.

## Why shazam2mqtt?

Streaming services expose what you're playing natively. **Physical media doesn't.**

If you consume music on:
- **Vinyl**
- **Cassette tapes**
- **CDs**
- **Radio**
- ...or anything else that doesn't have a Spotify API endpoint

...then Home Assistant has no idea what's spinning. `shazam2mqtt` fixes that by placing a microphone near your speakers, fingerprinting the audio with Shazam, and pushing the track metadata straight into HA.

Your dashboard can now show:
- What's currently playing
- The artist and track name
- Album artwork (Picture Entity card)
- A link to the song on Apple Music, Spotify, Deezer
- Lyrics, release metadata, and related videos
- Whether the room is silent or loud

## What it does

1. **Noise-gated listening** — continuously monitors ambient audio using an RMS threshold (`NOISE_GATE_DB`).
2. **Smart capture** — once audio is sustained for ~3 s, it records a 10-second clip.
3. **Shazam identification** — fingerprints the clip via `xazam` + `shazamio_core`.
4. **MQTT publishing** — pushes the track title, artist, and metadata to MQTT topics.
5. **Home Assistant discovery** — automatically registers 9 entities under one device (Now Playing, Artist, Track, Confidence, Matched, Status, Noise Level, Apple Music URL, Artwork URL) via the MQTT integration.
6. **Rich JSON attributes** — the Now Playing sensor carries lyrics, genres, Spotify/Deezer links, album metadata, and related YouTube videos as attributes.

## Quick Start (Docker Compose)

1. **Clone / copy** this directory.
2. **Create a `.env` file** (or export variables):

```bash
DEVICE_NAME=living_room
MQTT_HOST=192.168.1.200
MQTT_USER=mqtt
MQTT_PASS=secret
NOISE_GATE_DB=-40
LISTEN_DURATION=10
COOLDOWN_SECONDS=60
SAME_SONG_COOLDOWN_SECONDS=300
```

3. **Run:**

```bash
docker compose up --build
```

Home Assistant will auto-discover the device under **Settings → Devices & Services → MQTT**.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEVICE_NAME` | `shazam` | Prefix for the HA entity ID (`living_room_shazam_now_playing`) |
| `MQTT_HOST` | `localhost` | MQTT broker host |
| `MQTT_PORT` | `1883` | MQTT broker port |
| `MQTT_USER` | *(none)* | MQTT username |
| `MQTT_PASS` | *(none)* | MQTT password |
| `NOISE_GATE_DB` | `-40` | dBFS threshold. Audio quieter than this is considered silence. |
| `LISTEN_DURATION` | `10` | Seconds of audio to capture for Shazam recognition |
| `COOLDOWN_SECONDS` | `60` | Minimum seconds between recognition attempts |
| `SAME_SONG_COOLDOWN_SECONDS` | `300` | Extra cooldown if the same song repeats |
| `HA_DISCOVERY_PREFIX` | `homeassistant` | Home Assistant MQTT discovery prefix |
| `HA_ENABLED` | `true` | Set to `false` to disable HA discovery messages |
| `SAMPLE_RATE` | `44100` | Audio sample rate in Hz. Try `48000` if you get PortAudio invalid-sample-rate errors. |
| `SOUND_DEVICE` | *(none)* | PortAudio device index. Set if the default input device is wrong. Check container logs for the device list. |

## Architecture

```
Mic ──► Noise Gate (RMS) ──► 10 s Capture ──► Shazam API ──► MQTT ──► Home Assistant
                    │
                    └── "listen_now" command from HA
```

- **Idle loop** reads 1-second audio chunks and checks RMS energy.
- **Trigger** requires 3 consecutive "loud" chunks (~3 s hysteresis) to avoid reacting to pops.
- **State machine** prevents overlapping captures and rate-limits the Shazam API.
- **Command topic** `shazam2mqtt/<device_name>/command` accepts `listen_now` for manual triggers.

## MQTT Topics

| Topic | Type | Payload example |
|-------|------|-----------------|
| `shazam2mqtt/<name>/now_playing` | state | `Nothing Else Matters — Metallica` |
| `shazam2mqtt/<name>/status` | status | `playing` / `unknown` / `silence` |
| `shazam2mqtt/<name>/matched` | binary | `ON` / `OFF` |
| `shazam2mqtt/<name>/track` | sensor | `Nothing Else Matters` |
| `shazam2mqtt/<name>/artist` | sensor | `Metallica` |
| `shazam2mqtt/<name>/confidence` | sensor | `4` |
| `shazam2mqtt/<name>/apple_music_url` | sensor | `https://music.apple.com/...` |
| `shazam2mqtt/<name>/artwork_url` | sensor | `https://is1-ssl.mzstatic.com/...` |
| `shazam2mqtt/<name>/noise_level` | sensor | `-40.0` |
| `shazam2mqtt/<name>/command` | command in | `listen_now` |

## Audio Backends

### ALSA (default)
The `docker-compose.yml` passes `/dev/snd` into the container. This works on most headless Linux hosts.

### PulseAudio / PipeWire
If your host uses PulseAudio, comment out the `devices:` block and uncomment the `volumes:` and `PULSE_SERVER` lines in `docker-compose.yml`.

## Non-Docker Usage

```bash
pip install -e .
export DEVICE_NAME=my_room
export MQTT_HOST=192.168.1.200
python -m shazam2mqtt
```

## Troubleshooting

- **"No audio device found"** — make sure the container has access to `/dev/snd` or the PulseAudio socket.
- **"No matches" constantly** — lower `NOISE_GATE_DB` (e.g. `-50`) or move the mic closer to the speakers.
- **Entity not appearing in HA** — check that the MQTT integration is enabled in Home Assistant and that `HA_ENABLED=true`.

## License

MIT
