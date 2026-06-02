# shazam2mqtt Examples

## .env.example

A template environment file for Docker Compose.

```bash
cp examples/.env.example .env
# edit .env with your settings
docker compose up -d
```

## shazam2mqtt.service

A systemd unit for running the bridge natively (no Docker).

```bash
sudo cp examples/shazam2mqtt.service /etc/systemd/system/
sudo systemctl enable --now shazam2mqtt
```

## force_listen.py

Send a manual `listen_now` command via MQTT.

```bash
python examples/force_listen.py living_room 192.168.1.200 1883
```

This triggers an immediate capture regardless of the noise gate or cooldown.
