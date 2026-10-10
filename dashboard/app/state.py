"""
État patient « legacy » (comportement de l'ancien server.py, conservé à l'identique)
+ cache `room_state` par chambre pour les nouveaux scripts 3D.

Le message WebSocket `patient_event` et la structure `patients` ne changent pas :
le frontend existant (patient-state.js, avatars.js, dashboard-ui.js) en dépend.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from .bus import bus
from .ws import manager

logger = logging.getLogger("hackcure.state")

MAX_HISTORY = 100

# Même contenu que l'ancien server.py (ids, noms, âges, chambres, positions)
PATIENT_DEFAULTS: list[dict[str, Any]] = [
    {"patient_id": "patient_01", "name": "Patient A", "age": 72, "room": "101", "room_position": {"x": -4.0, "z": -4.0}},
    {"patient_id": "patient_02", "name": "Patient B", "age": 68, "room": "102", "room_position": {"x": 4.0, "z": -4.0}},
    {"patient_id": "patient_03", "name": "Patient C", "age": 81, "room": "103", "room_position": {"x": -4.0, "z": 4.0}},
    {"patient_id": "patient_04", "name": "Patient D", "age": 75, "room": "104", "room_position": {"x": 4.0, "z": 4.0}},
]


def _fresh_patient(base: dict[str, Any]) -> dict[str, Any]:
    return {
        **base,
        "state": "normal",
        "fall_detected": False,
        "pain_detected": False,
        "confidence": 0.0,
        "last_event_time": None,
        "alert_priority": "none",
        "source": "system",
    }


patients: dict[str, dict[str, Any]] = {p["patient_id"]: _fresh_patient(p) for p in PATIENT_DEFAULTS}
event_history: list[dict[str, Any]] = []
current_mode: dict[str, str] = {"mode": "demo"}

# room code -> patient_id (mis à jour par le seed / les admissions)
room_to_patient: dict[str, str] = {p["room"]: p["patient_id"] for p in PATIENT_DEFAULTS}

# Cache des états de chambre (contrat room_state, section 6.2)
room_states: dict[str, dict[str, Any]] = {}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def patient_for_room(room: str) -> str | None:
    return room_to_patient.get(str(room))


def room_for_patient(patient_id: str) -> str | None:
    p = patients.get(patient_id)
    return p["room"] if p else None


def register_patient(patient_id: str, name: str, age: int | None, room: str | None) -> None:
    """Ajoute/actualise un patient legacy (appelé par le seed et le CRUD patients)."""
    base = patients.get(patient_id) or _fresh_patient({"patient_id": patient_id, "name": name, "age": age, "room": room, "room_position": {"x": 0, "z": 0}})
    base["name"] = name
    base["age"] = age
    if room:
        # une chambre n'héberge qu'un patient actif
        for r, pid in list(room_to_patient.items()):
            if pid == patient_id and r != room:
                del room_to_patient[r]
        room_to_patient[str(room)] = patient_id
        base["room"] = str(room)
    patients[patient_id] = base


def unregister_patient(patient_id: str) -> None:
    patients.pop(patient_id, None)
    for r, pid in list(room_to_patient.items()):
        if pid == patient_id:
            del room_to_patient[r]


def state_from_flags(fall: bool, pain: bool) -> str:
    if fall and pain:
        return "fall_and_pain"
    if fall:
        return "fall_detected"
    if pain:
        return "pain_detected"
    return "normal"


async def process_event(
    patient_id: str,
    event_type: str,
    source: str = "demo",
    confidence: float = 0.90,
) -> dict[str, Any] | None:
    """Met à jour l'état d'un patient et diffuse `patient_event` (comportement d'origine)."""
    if patient_id not in patients:
        logger.warning("Unknown patient: %s", patient_id)
        return None

    patient = patients[patient_id]
    now = now_iso()

    if event_type == "fall":
        patient["fall_detected"], patient["pain_detected"] = True, False
        patient["state"], patient["alert_priority"] = "fall_detected", "critical"
    elif event_type == "pain":
        patient["fall_detected"], patient["pain_detected"] = False, True
        patient["state"], patient["alert_priority"] = "pain_detected", "high"
    elif event_type == "fall_and_pain":
        patient["fall_detected"], patient["pain_detected"] = True, True
        patient["state"], patient["alert_priority"] = "fall_and_pain", "critical"
    elif event_type == "recover":
        patient["fall_detected"], patient["pain_detected"] = False, False
        patient["state"], patient["alert_priority"] = "normal", "none"
    else:
        logger.warning("Unknown event type: %s", event_type)
        return None

    patient["confidence"] = confidence
    patient["last_event_time"] = now
    patient["source"] = source

    event = {
        "type": "patient_event",
        "patient_id": patient_id,
        "event_type": event_type,
        "source": source,
        "fall_detected": patient["fall_detected"],
        "pain_detected": patient["pain_detected"],
        "state": patient["state"],
        "confidence": confidence,
        "alert_priority": patient["alert_priority"],
        "timestamp": now,
        "room": patient.get("room"),
    }

    event_history.insert(0, event)
    if len(event_history) > MAX_HISTORY:
        event_history.pop()

    await manager.broadcast(event)
    await bus.publish(f"internal/patient_event/{patient_id}", event)
    logger.info("[%s] %s: %s (conf=%.2f)", source.upper(), patient_id, event_type, confidence)
    return event


async def reset_all(source: str = "system") -> None:
    for pid in list(patients):
        await process_event(pid, "recover", source=source, confidence=1.0)
    event_history.clear()
    await manager.broadcast({"type": "reset", "patients": patients})
    await bus.publish("internal/reset", {})


async def set_mode(mode: str) -> None:
    current_mode["mode"] = mode
    await manager.broadcast({"type": "mode_change", "mode": mode})
    await bus.publish("internal/mode", {"mode": mode})
    logger.info("Mode switched to: %s", mode)


def init_message() -> dict[str, Any]:
    """Message `init` envoyé à chaque nouveau client WebSocket (champs d'origine + extensions)."""
    return {
        "type": "init",
        "patients": patients,
        "mode": current_mode["mode"],
        "event_history": event_history[:20],
        "room_states": room_states,
    }
