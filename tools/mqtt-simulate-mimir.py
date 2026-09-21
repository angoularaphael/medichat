#!/usr/bin/env python3
"""Simule une alerte MIMIR sur le topic infirmerie (test local)."""

import json
import sys
from urllib.parse import urlparse

import paho.mqtt.client as mqtt

BROKER = sys.argv[1] if len(sys.argv) > 1 else "localhost"
TOPIC = "yggdrasil/mimir/security/infirmary"
PAYLOAD = {
    "alert": "stock_tampering",
    "drug_id": "paracetamol",
    "message": "Tentative de falsification des donnees de stock infirmerie",
}


def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id="mimir-simulator")
    client.connect(BROKER, 1883, 60)
    client.publish(TOPIC, json.dumps(PAYLOAD), qos=1)
    client.disconnect()
    print(f"Published to {TOPIC} on {BROKER}")


if __name__ == "__main__":
    main()
