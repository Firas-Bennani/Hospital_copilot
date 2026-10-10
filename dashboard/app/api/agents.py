"""Panneau Agents : statut des agents et journal (AgentLog)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from .. import auth as authlib
from ..agents import manager as agent_manager
from ..config import settings
from ..db import get_session
from ..models import AgentLog

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("")
def list_agents(_: authlib.CurrentUser = Depends(authlib.get_current_user)):
    return {"agents": agent_manager.infos(), "llm_provider": settings.llm_provider, "llm_model": settings.llm_model, "enabled": settings.agents_enabled}


@router.get("/logs")
def logs(agent: Optional[str] = None, room: Optional[str] = None, risk_id: Optional[int] = None, limit: int = Query(50, le=500), session: Session = Depends(get_session), _: authlib.CurrentUser = Depends(authlib.get_current_user)):
    q = select(AgentLog)
    if agent:
        q = q.where(AgentLog.agent == agent)
    if room:
        q = q.where(AgentLog.room_code == room)
    if risk_id:
        q = q.where(AgentLog.risk_id == risk_id)
    rows = session.exec(q.order_by(AgentLog.ts.desc()).limit(limit)).all()
    return [{"id": l.id, "agent": l.agent, "room": l.room_code, "input": l.input, "reasoning": l.reasoning, "output": l.output, "status": l.status, "risk_id": l.risk_id, "duration_ms": l.duration_ms, "ts": l.ts} for l in rows]
