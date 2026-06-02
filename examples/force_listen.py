"""Example: publish a manual "listen_now" command to MQTT.

Usage:
    python force_listen.py living_room

Requires:
    pip install paho-mqtt
"""

import sys
import paho.mqtt.client as mqtt


def main(device_name: str, host: str = "localhost", port: int = 1883):
    client = mqtt.Client()
    client.connect(host, port, 60)
    topic = f"shazam2mqtt/{device_name}/command"
    client.publish(topic, payload="listen_now")
    print(f"Published 'listen_now' to {topic}")
    client.disconnect()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <device_name> [mqtt_host] [mqtt_port]")
        sys.exit(1)
    main(
        sys.argv[1],
        sys.argv[2] if len(sys.argv) > 2 else "localhost",
        int(sys.argv[3]) if len(sys.argv) > 3 else 1883,
    )
