"""
VitalsAgent — seuils par métrique (ajustés au profil patient), tendances sur 10 min, NEWS2 déterministe,
alertes équipement (perfusion < 50 ml, occlusion, réaction transfusionnelle).
"""

from __future__ import annotations

import time
from typing import Any, Optional

from ..bus import Event, bus
from ..clinical.news2 import news2
from ..ingest import handler
from .base import Agent

# seuils par défaut : (type_de_risque, condition) — la sévérité fine est calculée par plans.severity_for
DEFAULT_LIMITS = {"hr_high": 112, "hr_low": 48, "spo2_low": 91, "sys_low": 95, "sys_high": 180, "temp_high": 38.0, "temp_low": 35.0, "rr_high": 25}
PERSIST = 3  # lectures consécutives hors limites avant alerte (anti-bruit)
SECONDARY = {"tachycardia", "bradycardia", "hypotension", "hypertension", "tachypnea", "hypoxemia"}


def limits_for(patient: Optional[dict[str, Any]]) -> dict[str, float]:
    lim = dict(DEFAULT_LIMITS)
    hist = ((patient or {}).get("history") or "").lower()
    if "bpco" in hist or "copd" in hist:
        lim["spo2_low"] = 88  # cible SpO2 88–92 % chez le BPCO
        lim["rr_high"] = 28
    if "fibrillation" in hist or "afib" in hist:
        lim["hr_high"] = 120
    return lim


class VitalsAgent(Agent):
    name = "VitalsAgent"
    description = "Surveille les constantes des machines : seuils par patient, tendances 10 min, NEWS2, alertes perfusion/transfusion."
    patterns = ["hackcure/room/+/device/+", "internal/reset"]
    tick_interval = 20.0

    def __init__(self) -> None:
        super().__init__()
        self.reported: dict[tuple[str, str], float] = {}
        self.active: dict[tuple[str, str], bool] = {}
        self.streak: dict[tuple[str, str], int] = {}
        self.limits_cache: dict[str, tuple[float, dict[str, float]]] = {}
        self.last_news2: dict[str, int] = {}
        from ..config import settings

        self.tick_interval = settings.vitals_tick_s

    def limits(self, room: str) -> dict[str, float]:
        cached = self.limits_cache.get(room)
        if cached and time.time() - cached[0] < 300:
            return cached[1]
        try:
            from ..db import session_scope
            from ..risks import patient_context

            with session_scope() as s:
                ctx = patient_context(s, room)
            lim = limits_for(ctx.get("patient"))
        except Exception:
            lim = dict(DEFAULT_LIMITS)
        self.limits_cache[room] = (time.time(), lim)
        return lim

    async def raise_candidate(self, room: str, rtype: str, details: dict[str, Any], reasoning: str, min_interval: float = 120.0) -> None:
        key = (room, rtype)
        now = time.time()
        self.streak[key] = self.streak.get(key, 0) + 1
        if self.streak[key] < PERSIST:
            return
        self.active[key] = True
        if now - self.reported.get(key, 0) < min_interval:
            return
        if rtype in SECONDARY and handler.room_state(room).get("riskLevel") == "critical":
            # conséquence probable d'un risque critique déjà ouvert (chute...) : noté, pas de doublon de risque
            if now - self.reported.get((room, "_secondary_note"), 0) > 120:
                self.reported[(room, "_secondary_note")] = now
                await self.log(room, input=", ".join(f"{k}={v}" for k, v in details.items()), reasoning=reasoning + " Un risque critique est déjà ouvert dans la chambre : signal rattaché, pas de nouveau risque.", output="noté sur le risque critique")
            return
        self.reported[key] = now
        async with self.working("acting"):
            await self.log(room, input=", ".join(f"{k}={v}" for k, v in details.items()), reasoning=reasoning, output=f"risque candidat « {rtype} »")
            await bus.publish("internal/risk_candidate", {"room": room, "type": rtype, "details": details, "source_agent": self.name})

    async def clear(self, room: str, rtype: str, reason: str) -> None:
        key = (room, rtype)
        self.streak[key] = 0
        if self.active.get(key):
            self.active[key] = False
            await bus.publish("internal/risk_clear", {"room": room, "types": [rtype], "reason": reason})

    async def handle(self, ev: Event) -> None:
        if ev.topic == "internal/reset":
            self.reported.clear()
            self.active.clear()
            self.streak.clear()
            return
        p = ev.payload
        room, d = p["room"], p["data"]
        t, m = d["type"], d.get("metrics", {})
        lim = self.limits(room)
        if t == "ecg" and m.get("hr") is not None:
            hr = float(m["hr"])
            if hr > lim["hr_high"]:
                await self.raise_candidate(room, "tachycardia", {"hr": hr, "rhythm": m.get("rhythm"), "limit": lim["hr_high"]}, f"FC {hr:.0f} bpm > seuil patient {lim['hr_high']} bpm (rythme {m.get('rhythm')}).")
            elif hr < lim["hr_low"]:
                await self.raise_candidate(room, "bradycardia", {"hr": hr, "limit": lim["hr_low"]}, f"FC {hr:.0f} bpm < seuil {lim['hr_low']} bpm.")
            else:
                await self.clear(room, "tachycardia", f"FC {hr:.0f} bpm normalisée")
                await self.clear(room, "bradycardia", f"FC {hr:.0f} bpm normalisée")
            if m.get("rr") is not None and float(m["rr"]) >= lim["rr_high"]:
                await self.raise_candidate(room, "tachypnea", {"rr": m["rr"], "limit": lim["rr_high"]}, f"FR {m['rr']}/min ≥ {lim['rr_high']}.")
        elif t == "spo2" and m.get("spo2") is not None:
            s = float(m["spo2"])
            if s < lim["spo2_low"]:
                await self.raise_candidate(room, "hypoxemia", {"spo2": s, "limit": lim["spo2_low"]}, f"SpO2 {s:.0f} % < seuil patient {lim['spo2_low']} %.")
            else:
                await self.clear(room, "hypoxemia", f"SpO2 {s:.0f} % normalisée")
        elif t == "bp" and m.get("sys") is not None:
            sy = float(m["sys"])
            if sy < lim["sys_low"]:
                await self.raise_candidate(room, "hypotension", {"sys": sy, "dia": m.get("dia"), "map": m.get("map"), "limit": lim["sys_low"]}, f"PAS {sy:.0f} mmHg < {lim['sys_low']} (PAM {m.get('map')}).")
            elif sy > lim["sys_high"]:
                await self.raise_candidate(room, "hypertension", {"sys": sy, "dia": m.get("dia"), "limit": lim["sys_high"]}, f"PAS {sy:.0f} mmHg > {lim['sys_high']}.")
            else:
                await self.clear(room, "hypotension", f"PAS {sy:.0f} mmHg normalisée")
                await self.clear(room, "hypertension", f"PAS {sy:.0f} mmHg normalisée")
        elif t == "thermometer" and m.get("tempC") is not None:
            tc = float(m["tempC"])
            if tc >= lim["temp_high"]:
                await self.raise_candidate(room, "fever", {"tempC": tc, "skinTempC": handler.room_state(room).get("skinTempC")}, f"Température {tc:.1f} °C ≥ {lim['temp_high']} °C (caméra thermique : {handler.room_state(room).get('skinTempC')} °C).")
            elif tc <= lim["temp_low"]:
                await self.raise_candidate(room, "hypothermia", {"tempC": tc}, f"Température {tc:.1f} °C ≤ {lim['temp_low']} °C.")
            else:
                await self.clear(room, "fever", f"température {tc:.1f} °C normalisée")
        elif t == "iv_pump":
            vol, occ = m.get("volumeLeftMl"), bool(m.get("occlusion"))
            if occ:
                await self.raise_candidate(room, "iv_occlusion", {"occlusion": True, "volumeLeftMl": vol}, "La pompe signale une occlusion de ligne.", min_interval=300)
            else:
                await self.clear(room, "iv_occlusion", "occlusion levée")
            if vol is not None and float(vol) < 50:
                await self.raise_candidate(room, "iv_empty", {"volumeLeftMl": vol, "rateMlH": m.get("rateMlH")}, f"Volume restant {vol} ml < 50 ml à {m.get('rateMlH')} ml/h.", min_interval=600)
            elif vol is not None and float(vol) > 100:
                await self.clear(room, "iv_empty", f"poche remplacée ({vol} ml)")
        elif t == "transfusion":
            if m.get("reaction"):
                await self.raise_candidate(room, "transfusion_reaction", {"reaction": True, "volumeLeftMl": m.get("volumeLeftMl")}, "Réaction transfusionnelle signalée par l'appareil : arrêt immédiat requis.", min_interval=300)
            else:
                await self.clear(room, "transfusion_reaction", "pas de réaction")

    async def on_tick(self) -> None:
        """NEWS2 et tendances 10 min pour chaque chambre."""
        for room in handler.ROOMS:
            v = handler.room_state(room).get("vitals") or {}
            if v.get("hr") is None or v.get("spo2") is None:
                continue
            res = news2(rr=v.get("rr"), spo2=v.get("spo2"), on_oxygen=bool((v.get("o2FlowLMin") or 0) > 0), sbp=v.get("sys"), hr=v.get("hr"), temp=v.get("tempC"))
            handler.room_state(room)["news2"] = res.to_dict()
            if res.score >= 5:
                await self.raise_candidate(room, "news2_high", {"news2": res.score, "components": res.components, **{k: v.get(k) for k in ("hr", "spo2", "sys", "tempC", "rr")}},
                                           f"NEWS2 = {res.score} ({res.band}) : composantes {res.components}.", min_interval=300)
            elif res.score <= 2:
                await self.clear(room, "news2_high", f"NEWS2 {res.score}")
            self.last_news2[room] = res.score
            # tendance sepsis : +1 °C et +20 bpm sur 10 min, ou PAS en baisse de 20 mmHg avec FC en hausse
            d_temp = self.delta(f"{room}-thermometer", "tempC", 600)
            d_hr = self.delta(f"{room}-ecg", "hr", 600)
            d_sys = self.delta(f"{room}-bp", "sys", 600)
            if (d_temp is not None and d_hr is not None and d_temp >= 0.8 and d_hr >= 18) or (d_sys is not None and d_hr is not None and d_sys <= -18 and d_hr >= 18):
                await self.raise_candidate(room, "sepsis_trend", {"deltaTemp10min": round(d_temp or 0, 1), "deltaHr10min": round(d_hr or 0), "deltaSys10min": round(d_sys or 0), "news2": res.score, "tempC": v.get("tempC"), "hr": v.get("hr"), "sys": v.get("sys")},
                                           f"Tendance 10 min : T° {d_temp:+.1f} °C, FC {d_hr:+.0f} bpm, PAS {d_sys or 0:+.0f} mmHg → profil évocateur de sepsis (NEWS2 {res.score}).", min_interval=600)

    @staticmethod
    def delta(device_id: str, metric: str, seconds: int) -> Optional[float]:
        pts = handler.device_history(device_id, metric, seconds)
        if len(pts) < 10:
            return None
        head = [v for _, v in pts[:5]]
        tail = [v for _, v in pts[-5:]]
        return sum(tail) / len(tail) - sum(head) / len(head)
