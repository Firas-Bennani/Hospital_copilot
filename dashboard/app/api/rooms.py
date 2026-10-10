"""Chambres : état temps réel (room_state), équipements, infos patient."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from .. import auth as authlib, state
from ..db import get_session
from ..ingest import handler
from ..models import Admission, Patient, Room, RoomEquipment

router = APIRouter(prefix="/api/rooms", tags=["rooms"])


def _room_payload(session: Session, room: Room) -> dict:
    rs = handler.room_state(room.code)
    adm = session.exec(select(Admission).where(Admission.room_code == room.code, Admission.discharged_at.is_(None))).first()
    patient = session.get(Patient, adm.patient_id) if adm else None
    eq = {e.type: e.state for e in session.exec(select(RoomEquipment).where(RoomEquipment.room_code == room.code)).all()}
    return {
        "code": room.code, "type": room.type, "is_real_instrumented": room.is_real_instrumented, "wing": room.wing,
        "edge_alive": handler.edge_alive(room.code),
        "equipment": {**eq, **rs.get("equipment", {})},
        "patient": None if not patient else {"patient_id": patient.patient_id, "code": patient.code, "display_name": patient.display_name, "full_name": patient.full_name, "age": patient.age, "fall_risk": patient.fall_risk, "allergies": patient.allergies},
        "admission": None if not adm else {"id": adm.id, "admitted_at": adm.admitted_at, "reason": adm.reason, "referring_doctor": adm.referring_doctor},
        "state": rs,
    }


@router.get("")
def list_rooms(session: Session = Depends(get_session), _: authlib.CurrentUser = Depends(authlib.get_current_user)):
    return [_room_payload(session, r) for r in session.exec(select(Room).order_by(Room.code)).all()]


@router.get("/states")
def room_states(_: authlib.CurrentUser = Depends(authlib.get_current_user)):
    return {r: handler.room_state(r) for r in handler.ROOMS}


@router.get("/{code}")
def get_room(code: str, session: Session = Depends(get_session), _: authlib.CurrentUser = Depends(authlib.get_current_user)):
    room = session.exec(select(Room).where(Room.code == code)).first()
    if not room:
        raise HTTPException(404, "Chambre inconnue")
    return _room_payload(session, room)


@router.get("/{code}/legacy")
def legacy(code: str, _: authlib.CurrentUser = Depends(authlib.get_current_user)):
    pid = state.patient_for_room(code)
    return state.patients.get(pid) if pid else None
