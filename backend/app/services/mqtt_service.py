import json
import logging
import threading
from urllib.parse import urlparse

import paho.mqtt.client as mqtt
from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import SessionLocal
from app.models.entities import SecurityAlert

logger = logging.getLogger("eir.mqtt")

_client: mqtt.Client | None = None
_lock = threading.Lock()


def _on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
    except json.JSONDecodeError:
        payload = {"raw": msg.payload.decode("utf-8", errors="replace")}

    db = SessionLocal()
    try:
        alert = SecurityAlert(source="mimir_infirmary", payload=payload)
        db.add(alert)
        db.commit()
        logger.info("Security alert stored from %s", msg.topic)
    finally:
        db.close()


def start_mqtt_background() -> None:
    global _client
    with _lock:
        if _client is not None:
            return

        parsed = urlparse(settings.mqtt_broker)
        host = parsed.hostname or "mqtt"
        port = parsed.port or 1883

        client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION1,
            client_id=settings.mqtt_client_id,
        )
        client.on_message = _on_message

        try:
            client.connect(host, port, keepalive=60)
            client.subscribe("yggdrasil/mimir/security/infirmary")
            client.loop_start()
            _client = client
            logger.info("MQTT connected to %s:%s", host, port)
        except Exception as exc:
            logger.warning("MQTT unavailable: %s", exc)


def publish(topic: str, payload: dict) -> bool:
    global _client
    if _client is None:
        start_mqtt_background()
    if _client is None:
        return False
    try:
        _client.publish(topic, json.dumps(payload), qos=1)
        return True
    except Exception as exc:
        logger.warning("MQTT publish failed: %s", exc)
        return False


def publish_crisis(sick_ratio: float, autonomy_days: float) -> None:
    publish(
        "yggdrasil/eir/alert/crisis",
        {"level": "epidemic", "sick_ratio": sick_ratio, "autonomy_days": autonomy_days},
    )


def publish_stock_low(drug_id: str, remaining_units: int) -> None:
    publish(
        "yggdrasil/eir/stock/low",
        {"drug_id": drug_id, "remaining_units": remaining_units},
    )


def list_security_alerts(db: Session, limit: int = 20) -> list[SecurityAlert]:
    return (
        db.query(SecurityAlert)
        .order_by(SecurityAlert.created_at.desc())
        .limit(limit)
        .all()
    )
