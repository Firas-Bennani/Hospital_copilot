"""Petits utilitaires communs aux agents (heure de nuit, vitals, NEWS2 courant)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from ..clinical.news2 import News2Result, news2
from ..ingest import handler


def is_night() -> bool:
    try:
        from ..sim import embedded

        if embedded.engine is not None and embedded.engine.night_override is not None:
            return bool(embedded.engine.night_override)
    except Exception:
        pass
    h = datetime.now().hour
    return h >= 22 or h < 6


def room_vitals(room: str) -> dict[str, Any]:
    return dict(handler.room_state(room).get("vitals") or {})


def current_news2(room: str) -> Optional[News2Result]:
    v = room_vitals(room)
    if v.get("hr") is None and v.get("spo2") is None:
        return None
    return news2(rr=v.get("rr"), spo2=v.get("spo2"), on_oxygen=bool((v.get("o2FlowLMin") or 0) > 0), sbp=v.get("sys"), hr=v.get("hr"), temp=v.get("tempC"))


def short(d: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    return {k: d.get(k) for k in keys if d.get(k) is not None}
