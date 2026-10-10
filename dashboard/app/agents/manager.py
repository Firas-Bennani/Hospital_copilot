"""Démarrage et registre des 6 agents."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from ..config import settings
from .base import Agent
from .environment import EnvironmentAgent
from .followup import FollowUpAgent
from .report import ReportAgent
from .risk import RiskAgent
from .vision import VisionAgent
from .vitals import VitalsAgent

logger = logging.getLogger("hackcure.agents")

agents: dict[str, Agent] = {}


async def start() -> list[asyncio.Task]:
    if not settings.agents_enabled:
        logger.info("Agents désactivés (AGENTS_ENABLED=0)")
        return []
    tasks = []
    for cls in (VisionAgent, VitalsAgent, EnvironmentAgent, RiskAgent, FollowUpAgent, ReportAgent):
        a = cls()
        agents[a.name] = a
        tasks.append(a.start())
    logger.info("Agents démarrés : %s", ", ".join(agents))
    return tasks


def get(name: str) -> Optional[Agent]:
    return agents.get(name)


def report_agent() -> ReportAgent:
    a = agents.get("ReportAgent")
    if a is None:
        a = ReportAgent()  # utilisable même si les agents sont désactivés
        agents[a.name] = a
    return a  # type: ignore[return-value]


def infos() -> list[dict[str, Any]]:
    return [a.info() for a in agents.values()]
