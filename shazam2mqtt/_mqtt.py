"""Paho MQTT client factory that works on paho-mqtt 1.x and 2.x.

paho-mqtt 2.0 made ``callback_api_version`` a required constructor argument and
changed the callback signatures. This wraps the difference in one place so the
rest of the package builds a client without caring which version is installed.
"""

import paho.mqtt.client as mqtt


def new_client(client_id: str):
    """Return an MQTT client, preferring the modern v2 callback API."""
    try:
        return mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
    except (AttributeError, TypeError):  # paho-mqtt 1.x
        return mqtt.Client(client_id=client_id)
