"""
Endpoints d'origine (démo, mode, YOLO) — comportement inchangé.
Restent accessibles sans authentification en mode démo (règle du prompt).
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .. import state

router = APIRouter(tags=["legacy"])


class DemoEvent(BaseModel):
    patient_id: str
    event_type: str  # "fall", "pain", "fall_and_pain", "recover"
    confidence: float = 0.90


class ModeSwitch(BaseModel):
    mode: str  # "demo" or "real"


@router.get("/api/patients")
async def get_patients():
    """État courant de tous les patients (structure legacy)."""
    return JSONResponse(content=state.patients)


@router.get("/api/events")
async def get_events():
    return JSONResponse(content=state.event_history[:50])


@router.post("/api/demo/trigger")
async def trigger_demo_event(event: DemoEvent):
    if state.current_mode["mode"] != "demo":
        return JSONResponse(content={"error": "Demo events only allowed in demo mode"}, status_code=400)
    await state.process_event(
        patient_id=event.patient_id,
        event_type=event.event_type,
        source="simulation",
        confidence=event.confidence,
    )
    return JSONResponse(content={"status": "ok", "event": event.event_type})


@router.post("/api/demo/reset")
async def reset_demo():
    await state.reset_all()
    return JSONResponse(content={"status": "reset"})


@router.post("/api/mode")
async def switch_mode(mode: ModeSwitch):
    if mode.mode not in ("demo", "real"):
        return JSONResponse(content={"error": "Mode must be 'demo' or 'real'"}, status_code=400)
    await state.set_mode(mode.mode)
    return JSONResponse(content={"status": "ok", "mode": mode.mode})


@router.post("/api/yolo/event")
async def receive_yolo_event(event: DemoEvent):
    """Événements YOLO réels envoyés par camera_loop.py (scénario A)."""
    await state.process_event(
        patient_id=event.patient_id,
        event_type=event.event_type,
        source="yolo",
        confidence=event.confidence,
    )
    return JSONResponse(content={"status": "ok"})
