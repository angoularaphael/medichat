import json
import logging
import os
import threading
from pathlib import Path
from urllib.parse import urlparse

import paho.mqtt.client as mqtt
from sqlalchemy.orm import Session

from app.config import settings
from app.db import session as db_session
from app.models.entities import SecurityAlert
from app.services import journal

logger = logging.getLogger("eir.mqtt")
OUTBOX = Path(__file__).resolve().parents[2] / "data" / "offline_outbox.jsonl"

_client: mqtt.Client | None = None
_lock = threading.Lock()


INFIRMARY_TOPIC = "yggdrasil/mimir/security/infirmary"


def _on_connect(client, userdata, flags, rc):
    if rc != 0:
        logger.warning("MQTT connexion refusee: %s", rc)
        return
    client.subscribe(INFIRMARY_TOPIC, qos=1)
    logger.info("MQTT abonne a %s", INFIRMARY_TOPIC)


def _on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
    except json.JSONDecodeError:
        payload = {"raw": msg.payload.decode("utf-8", errors="replace")}
    if not isinstance(payload, dict):
        payload = {"raw": payload}

    text = str(payload.get("message") or payload.get("alert") or "Alerte reseau")
    db = db_session.SessionLocal()
    try:
        db.add(SecurityAlert(source="mimir_infirmary", payload=payload))
        db.commit()
        journal.log_decision(
            db,
            action="mimir_alert",
            summary=f"MIMIR: {text}",
            payload=payload,
        )
        logger.info("Alerte MIMIR enregistree")
    except Exception:
        logger.exception("Alerte MIMIR non enregistree")
        db.rollback()
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
            client_id=f"{settings.mqtt_client_id}-{os.getpid()}",
        )
        client.on_connect = _on_connect
        client.on_message = _on_message
        client.reconnect_delay_set(min_delay=1, max_delay=20)

        try:
            client.connect(host, port, keepalive=60)
            client.loop_start()
            _client = client
            logger.info("MQTT connected to %s:%s", host, port)
        except Exception as exc:
            logger.warning("MQTT unavailable: %s", exc)


def is_connected() -> bool:
    return _client is not None and _client.is_connected()


def _enqueue(topic: str, payload: dict) -> None:
    OUTBOX.parent.mkdir(parents=True, exist_ok=True)
    with OUTBOX.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"topic": topic, "payload": payload}) + "\n")


def pending_outbox() -> int:
    if not OUTBOX.exists():
        return 0
    return sum(1 for line in OUTBOX.read_text(encoding="utf-8").splitlines() if line.strip())


def publish(topic: str, payload: dict) -> bool:
    global _client
    if _client is None:
        start_mqtt_background()
    if _client is None or not is_connected():
        _enqueue(topic, payload)
        return False
    try:
        _client.publish(topic, json.dumps(payload), qos=1)
        return True
    except Exception as exc:
        logger.warning("MQTT publish failed: %s", exc)
        _enqueue(topic, payload)
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
