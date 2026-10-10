"""
Client MQTT optionnel (aiomqtt). S'abonne à `hackcure/#` et relaie vers `handler.handle`.
Si le broker ne répond pas : état `unavailable`, nouvelles tentatives périodiques, et tout
passe par le repli HTTP `POST /api/ingest` (aucune action requise).
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Optional

from .. import contracts
from ..config import settings
from . import handler

logger = logging.getLogger("hackcure.mqtt")

_client = None
_status = "disabled"
_task: Optional[asyncio.Task] = None
_lock = asyncio.Lock()


def status() -> str:
    return _status


def connected() -> bool:
    return _status == "connected"


async def start() -> list[asyncio.Task]:
    global _task, _status
    if not settings.mqtt_enabled:
        _status = "disabled"
        return []
    try:
        import aiomqtt  # noqa: F401
    except ImportError:
        _status = "unavailable (aiomqtt manquant)"
        logger.warning("aiomqtt non installé : repli HTTP")
        return []
    _status = "connecting"
    _task = asyncio.create_task(_run(), name="mqtt-client")
    return [_task]


async def _run() -> None:
    global _client, _status
    import aiomqtt

    backoff = 5.0
    while True:
        try:
            async with aiomqtt.Client(settings.mqtt_host, settings.mqtt_port, timeout=5) as client:
                _client = client
                _status = "connected"
                backoff = 5.0
                logger.info("MQTT connecté à %s:%s", settings.mqtt_host, settings.mqtt_port)
                await client.subscribe(f"{settings.mqtt_prefix}/#")
                async for message in client.messages:
                    topic = str(message.topic)
                    try:
                        payload = json.loads(message.payload.decode("utf-8"))
                    except Exception:
                        logger.warning("MQTT payload non JSON sur %s", topic)
                        continue
                    if not isinstance(payload, dict):
                        continue
                    try:
                        await handler.handle(topic, payload, via="mqtt")
                    except contracts.ContractError as exc:
                        logger.warning("MQTT message invalide %s: %s", topic, exc)
                    except Exception:
                        logger.exception("MQTT handler")
        except asyncio.CancelledError:
            _status = "stopped"
            raise
        except Exception as exc:
            _client = None
            _status = "unavailable"
            logger.info("Broker MQTT indisponible (%s) — repli HTTP actif, nouvel essai dans %.0fs", exc.__class__.__name__, backoff)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60.0)


async def publish(topic: str, payload: dict[str, Any]) -> bool:
    """Publie si connecté ; renvoie False sinon (l'appelant utilise un autre canal)."""
    if _client is None or _status != "connected":
        return False
    try:
        async with _lock:
            await _client.publish(topic, json.dumps(payload, default=str).encode("utf-8"), qos=1)
        return True
    except Exception as exc:
        logger.warning("Publication MQTT échouée: %s", exc)
        return False
