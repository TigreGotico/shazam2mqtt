# shazam2mqtt

`shazam2mqtt` is a Dockerized bridge that listens to a room, identifies the music playing through Shazam, and publishes the result to MQTT, including Home Assistant auto-discovery.

## Why shazam2mqtt

Streaming services report what is playing on their own. Physical media does not. If music comes from vinyl, cassette tapes, CDs, radio, or any other source without a streaming API, Home Assistant has no way to know what is playing. `shazam2mqtt` places a microphone near the speakers, fingerprints the audio with Shazam, and sends the track metadata to Home Assistant.

A dashboard built on this data can show:
- The current track, artist, and album artwork
- A link to the song on Apple Music, Spotify, or Deezer
- Lyrics, release metadata, and related videos
- Whether the room is silent or playing audio

## What it does

1. **Noise-gated listening**: monitors ambient audio using an RMS threshold (`NOISE_GATE_DB`).
2. **Smart capture**: after audio stays above the threshold for about 3 seconds, it records a 10-second clip.
3. **Shazam identification**: fingerprints the clip with [`xazam`](https://pypi.org/project/xazam/) and `shazamio_core`.
4. **Extra track info**: after a match, queries Shazam for lyrics, release metadata (album, label, date), and related YouTube videos.
5. **MQTT publishing**: sends the track title, artist, and metadata to MQTT topics.
6. **Home Assistant discovery**: registers 10 entities under one "Shazam" device through the MQTT integration.
7. **Rich JSON attributes**: the Now Playing sensor carries lyrics, genres, Spotify/Deezer links, album metadata, and related YouTube videos as attributes.

## Quick start (Docker Compose)

1. Copy this directory.
2. Create a `.env` file (or export the variables):

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

3. Run:

```bash
docker compose pull
docker compose up -d
```

Home Assistant discovers the device under **Settings → Devices & Services → MQTT**.

## Environment variables

All settings are optional. Defaults work for most setups.

| Variable | Default | Description |
|----------|---------|-------------|
| `DEVICE_NAME` | `shazam` | Prefix for the HA entity ID (`living_room_shazam_now_playing`) |
| `MQTT_HOST` | `localhost` | MQTT broker host |
| `MQTT_PORT` | `1883` | MQTT broker port |
| `MQTT_USER` | *(none)* | MQTT username |
| `MQTT_PASS` | *(none)* | MQTT password |
| `NOISE_GATE_DB` | `-40` | dBFS threshold. Audio quieter than this counts as silence. |
| `LISTEN_DURATION` | `10` | Seconds of audio to capture for Shazam recognition |
| `COOLDOWN_SECONDS` | `10` | Minimum seconds between two recognition attempts |
| `SAME_SONG_COOLDOWN_SECONDS` | `30` | Cooldown used instead of the normal one when the same song is detected twice in a row. Set higher to avoid re-identifying the same long track. |
| `HA_DISCOVERY_PREFIX` | `homeassistant` | Home Assistant MQTT discovery prefix |
| `HA_ENABLED` | `true` | Set to `false` to disable HA discovery messages |
| `SAMPLE_RATE` | `44100` | Audio sample rate in Hz. Try `48000` if you get PortAudio invalid-sample-rate errors. |
| `SOUND_DEVICE` | *(none)* | PortAudio device index. Set this if the default input device is wrong. Check the container logs for the device list. |
| `ALSA_CARD` | *(none)* | ALSA card name (for example `C615`). Forces the default capture device on PipeWire/ALSA hosts without setting a PortAudio index. |
| `NOISE_LEVEL_INTERVAL` | `5.0` | Minimum seconds between Noise Level sensor MQTT updates. |
| `NOISE_LEVEL_DELTA` | `3.0` | dB change required to publish a Noise Level update immediately, bypassing the interval. |
| `REQUIRED_NO_MATCHES` | `2` | Consecutive "no match" results from Shazam before the state changes from `playing` to `unknown/no-match`. Prevents brief drop-outs from resetting the display mid-track. |
| `QUIET_HYSTERESIS` | `5` | Seconds of quiet audio before the state changes to `silent`. |

### Tuning the noise gate

If music is playing but the gate never triggers:
- Check the **Noise Level** sensor in HA. If it stays below the threshold, lower `NOISE_GATE_DB` (for example `-60`).
- If the value stays at `-75` even during playback, the mic gain is too low or the wrong device is selected.

### Tuning cooldowns

| Scenario | Suggested values |
|----------|------------------|
| Fast switching (radio, shuffle) | `COOLDOWN_SECONDS=5` `SAME_SONG_COOLDOWN_SECONDS=10` |
| Normal listening | `COOLDOWN_SECONDS=10` `SAME_SONG_COOLDOWN_SECONDS=30` (defaults) |
| Long tracks / ambient | `COOLDOWN_SECONDS=15` `SAME_SONG_COOLDOWN_SECONDS=120` |

## Architecture

```
Mic ──► Noise Gate (RMS) ──► 10 s Capture ──► xazam.identify()
                                                   │
                                                   ▼
                                          get_track_info() ──► lyrics, metadata, videos
                                                   │
                                                   ▼
                                               MQTT ──► Home Assistant
```

- The **idle loop** reads 1-second audio chunks and checks the RMS energy.
- The **trigger** requires 3 consecutive "loud" chunks (about 3 seconds of hysteresis) to avoid reacting to pops.
- The **state machine** has three states and prevents brief drop-outs from resetting the display:
  - `playing`: Shazam matched a track.
  - `unknown/no-match`: the room is loud but Shazam failed after `REQUIRED_NO_MATCHES` consecutive attempts.
  - `silence`: the room has been quiet for `QUIET_HYSTERESIS` seconds.
- The **command topic** `shazam2mqtt/<device_name>/command` accepts `listen_now` for manual triggers.

## Home Assistant entities (10 under one device)

| Entity | Type | Payload / Example |
|--------|------|-------------------|
| Now Playing | sensor + attrs | `Nothing Else Matters - Metallica` + JSON attrs |
| Status | sensor | `playing` / `unknown` / `silence` |
| Matched | binary_sensor | `ON` / `OFF` |
| Track | sensor | `Nothing Else Matters` |
| Artist | sensor | `Metallica` |
| Confidence | sensor | `4` (match count) |
| Apple Music URL | sensor | `https://music.apple.com/...` |
| Artwork URL | sensor | `https://is1-ssl.mzstatic.com/...` |
| Noise Level | sensor | `-40.0` dBFS |
| Command | command in | `listen_now` |

The **Now Playing** sensor carries rich JSON attributes:
```json
{
  "artist": "Metallica",
  "title": "Nothing Else Matters",
  "confidence": 4,
  "apple_music_url": "...",
  "artwork_url": "...",
  "spotify_url": "...",
  "deezer_url": "...",
  "shazam_url": "...",
  "lyrics": "...",
  "genres": ["Metal"],
  "metadata": {"Album": "Metallica", "Released": "1991", "Label": "Elektra"},
  "related_videos": ["https://youtube.com/watch?v=..."]
}
```

### Dashboard tips

- **Artwork:** add a Picture Entity card that uses the `Artwork URL` sensor.
- **Now Playing details:** add a Markdown card with `{{ state_attr('sensor.living_room_shazam_now_playing', 'lyrics') }}`.
- **Quick link:** add a button that opens `{{ state_attr('sensor.living_room_shazam_now_playing', 'apple_music_url') }}`.

## Audio backends

### ALSA (default)
The `docker-compose.yml` passes `/dev/snd` into the container. This works on most headless Linux hosts.

### PipeWire
If the host runs PipeWire, set the ALSA card name so the container uses the right mic:

```bash
# Find the capture card name on the host
arecord -l
# Look for: card X: NAME [Human Readable Name]
# Example: card 3: C615 [HD Webcam C615]
```

Then in `.env`:
```bash
ALSA_CARD=C615
```

This is more reliable than `SOUND_DEVICE` because it survives card-number reordering.

### PulseAudio (legacy)
If the host uses pure PulseAudio (not PipeWire), comment out the `devices:` block and uncomment the `volumes:` / `PULSE_SERVER` lines in `docker-compose.yml`.

## MQTT topics

| Topic | Type | Payload example |
|-------|------|-----------------|
| `shazam2mqtt/<name>/now_playing` | state | `Nothing Else Matters - Metallica` |
| `shazam2mqtt/<name>/status` | status | `playing` / `unknown/no-match` / `silence` |
| `shazam2mqtt/<name>/matched` | binary | `ON` / `OFF` |
| `shazam2mqtt/<name>/track` | sensor | `Nothing Else Matters` |
| `shazam2mqtt/<name>/artist` | sensor | `Metallica` |
| `shazam2mqtt/<name>/confidence` | sensor | `4` |
| `shazam2mqtt/<name>/apple_music_url` | sensor | `https://music.apple.com/...` |
| `shazam2mqtt/<name>/artwork_url` | sensor | `https://is1-ssl.mzstatic.com/...` |
| `shazam2mqtt/<name>/noise_level` | sensor | `-40.0` |
| `shazam2mqtt/<name>/command` | command in | `listen_now` |

## Troubleshooting

### "No audio device found"
Make sure the container has access to `/dev/snd` or the PulseAudio socket. On the host, run:
```bash
arecord -l
```
If no capture devices appear, the host itself cannot see a mic.

### "Invalid sample rate" (PortAudio error -9997)
The mic does not support the default 44100 Hz. Try:
```bash
SAMPLE_RATE=48000
```
Or for cheap webcams:
```bash
SAMPLE_RATE=16000
```

### Noise level stuck at -75 dBFS (silence) even when music is playing
The container is reading from the wrong device, or the capture volume is muted.

1. Check the startup logs for the device list:
   ```bash
   docker logs shazam2mqtt --tail 20
   ```
2. If the default device looks wrong, set the correct one:
   ```bash
   # Option A: PipeWire / ALSA card name (recommended)
   ALSA_CARD=C615

   # Option B: PortAudio device index
   SOUND_DEVICE=2
   ```
3. Check the host ALSA capture volume:
   ```bash
   alsamixer -c 2   # replace 2 with your card number
   ```
   Press `F4` for the Capture view. Make sure it is not muted (`MM`) and the volume is high.

### "No matches" constantly
- Lower `NOISE_GATE_DB` (for example `-60`) so quieter audio triggers the gate.
- Move the mic closer to the speakers.
- Increase `LISTEN_DURATION` to give Shazam more audio to fingerprint.

### Entity not appearing in HA
- Check that the MQTT integration is enabled in Home Assistant.
- Verify `HA_ENABLED=true`.
- Check that the broker credentials (`MQTT_HOST`, `MQTT_USER`, `MQTT_PASS`) are correct.

## Non-Docker usage

```bash
pip install -e .
export DEVICE_NAME=my_room
export MQTT_HOST=192.168.1.200
python -m shazam2mqtt
```

## Related projects

- [pyshazam](https://github.com/TigreGotico/pyshazam): the Shazam client library this project builds on.
- [vad2mqtt](https://github.com/TigreGotico/vad2mqtt): a similar bridge for voice activity detection.
- [linux2mqtt](https://github.com/TigreGotico/linux2mqtt): publishes Linux desktop state to MQTT.

## License

MIT
