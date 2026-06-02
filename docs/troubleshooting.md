# Troubleshooting

## "No audio device found" in Docker

- Ensure the container has access to `/dev/snd` (ALSA) or the PulseAudio socket.
- On the host, run `arecord -l` to verify the mic is visible to ALSA.

## "No matches" constantly

- Lower `NOISE_GATE_DB` (e.g. `-50`) so quieter audio triggers capture.
- Move the mic closer to the speakers.
- Check that the captured audio is clean (use `mic_recording.py` to record a sample and listen to it).

## Entity not appearing in Home Assistant

- Verify the MQTT integration is configured in HA.
- Check that `HA_ENABLED=true`.
- Look for discovery messages under `homeassistant/sensor/<name>_shazam_*/config` in your MQTT broker.

## Shazam rate limiting

If you see frequent `429` errors:
- Increase `COOLDOWN_SECONDS`.
- Ensure `SAME_SONG_COOLDOWN_SECONDS` is high enough to prevent duplicate hits.

## High CPU / continuous captures

- Check the noise level sensor in HA. If it hovers near your threshold, lower `NOISE_GATE_DB` by 5–10 dB.
- Ensure the mic is not picking up constant background noise (fans, AC).
