"""
EnvironmentAgent — confort thermique : > 27 °C clim, < 19 °C chauffage, fenêtre fermée si l'un est actif,
retour au repos entre 21 et 25 °C. Envoie `cmd/*`, attend `cmd/ack`, ne contredit jamais une règle locale
(alarme locale récente ou refus de l'edge) et ne force pas une commande manuelle récente.
"""

from __future__ import annotations

import time
from typing import Any

from ..bus import Event, bus
from ..ingest import handler
from .base import Agent

COOLDOWN_S = 90.0
MANUAL_HOLD_S = 600.0


class EnvironmentAgent(Agent):
    name = "EnvironmentAgent"
    description = "Veille au confort thermique et pilote fenêtre, chauffage et climatisation (sans contredire les règles locales de l'edge)."
    patterns = ["hackcure/room/+/env", "hackcure/room/+/cmd/ack", "hackcure/room/+/cmd/+", "internal/reset"]
    tick_interval = 60.0

    def __init__(self) -> None:
        super().__init__()
        self.last_action: dict[str, float] = {}
        self.manual_until: dict[str, float] = {}
        self.local_refusal: dict[str, float] = {}
        self.pending_manual: dict[tuple[str, str], tuple[str, str, str]] = {}

    async def handle(self, ev: Event) -> None:
        if ev.topic == "internal/reset":
            self.last_action.clear()
            return
        p = ev.payload
        room, kind, d = p["room"], p["kind"], p["data"]
        if kind == "cmd":
            if d.get("requestedBy") and d["requestedBy"] != self.name and d.get("source") == "server":
                self.manual_until[room] = time.time() + MANUAL_HOLD_S  # un humain (ou n8n) a la main
                self.pending_manual[(room, p.get("groups", {}).get("equipment") or "")] = (d["requestedBy"], d.get("action"), d.get("reason") or "")
            return
        if kind == "cmd_ack":
            who = self.pending_manual.pop((room, d.get("equipment") or ""), None)
            if who:
                await self.log(room, input=f"commande de {who[0]} : {d.get('equipment')} → {who[1]} ({who[2] or 'sans motif'})",
                               reasoning="Commande d'équipement demandée hors EnvironmentAgent : exécutée telle quelle, l'agent s'abstient pendant 10 min. Mesure de confort : elle n'agit sur aucun risque clinique.",
                               output=f"{d.get('equipment')} = {d.get('state')}" if d.get("ok") else f"refusée : {d.get('error') or 'sans accusé'}", status="ok" if d.get("ok") else "error")
            if not d.get("ok") and d.get("error"):
                self.local_refusal[room] = time.time()
                await self.log(room, input=f"ack {d.get('equipment')}/{d.get('action')} refusé : {d.get('error')}", reasoning="Une règle locale de l'edge a priorité : on n'insiste pas pendant 5 min.", output="commande abandonnée")
            return
        if kind != "env":
            return
        await self.evaluate(room, float(d["tempC"]), bool(d.get("doorOpen", False)))

    async def evaluate(self, room: str, temp: float, door_open: bool) -> None:
        now = time.time()
        rs = handler.room_state(room)
        eq = rs.get("equipment", {})
        if now - self.last_action.get(room, 0) < COOLDOWN_S:
            return
        if now < self.manual_until.get(room, 0):
            return
        if now - self.local_refusal.get(room, 0) < 300:
            return
        alarm = rs.get("localAlarm")
        if alarm and alarm.get("reason") in ("fall", "critical"):
            return  # ne jamais interférer pendant une alarme locale

        actions: list[tuple[str, str, str]] = []
        if temp > 27.0 and eq.get("ac") != "on":
            actions.append(("ac", "on", f"température {temp:.1f} °C > 27 °C"))
            if eq.get("window") == "open":
                actions.append(("window", "close", "climatisation active"))
            if eq.get("heater") == "on":
                actions.append(("heater", "off", "climatisation active"))
        elif temp < 19.0 and eq.get("heater") != "on":
            actions.append(("heater", "on", f"température {temp:.1f} °C < 19 °C"))
            if eq.get("window") == "open":
                actions.append(("window", "close", "chauffage actif"))
            if eq.get("ac") == "on":
                actions.append(("ac", "off", "chauffage actif"))
        elif 21.0 <= temp <= 25.0:
            if eq.get("ac") == "on":
                actions.append(("ac", "off", f"température {temp:.1f} °C confortable"))
            if eq.get("heater") == "on":
                actions.append(("heater", "off", f"température {temp:.1f} °C confortable"))
        if temp > 30.0 or temp < 16.0:
            await bus.publish("internal/risk_candidate", {"room": room, "type": "thermal_discomfort", "details": {"tempC": round(temp, 1), "window": eq.get("window"), "heater": eq.get("heater"), "ac": eq.get("ac")}, "source_agent": self.name})
        if not actions:
            return
        self.last_action[room] = now
        from ..commands import send_command

        async with self.working("acting"):
            results = []
            for equipment, action, why in actions:
                r = await send_command(room, equipment, action, requested_by=self.name, reason=why)
                results.append(f"{equipment} {action} → {'ack ' + str(r['ack'].get('state')) if r['ok'] else 'sans ack'} ({r['transport']})")
            await self.log(room, input=f"tempC={temp:.1f}, porte {'ouverte' if door_open else 'fermée'}, équipements {eq}",
                           reasoning="Règles : > 27 °C → clim ; < 19 °C → chauffage ; fenêtre fermée si l'un est actif ; 21–25 °C → repos. Commande manuelle récente ou règle locale → abstention.",
                           output="; ".join(results))

    async def on_tick(self) -> None:
        for room in handler.ROOMS:
            t = handler.room_state(room)["env"].get("tempC")
            if t is not None:
                await self.evaluate(room, float(t), bool(handler.room_state(room)["env"].get("doorOpen")))
