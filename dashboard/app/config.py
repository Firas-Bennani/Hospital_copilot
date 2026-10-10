"""
Configuration centrale (variables d'environnement, fichier .env à la racine).
Aucun secret dans le code : les valeurs par défaut sont des valeurs de démo.
"""

from __future__ import annotations

import os
from pathlib import Path

try:  # python-dotenv est optionnel
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

DASHBOARD_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = DASHBOARD_DIR.parent
STATIC_DIR = DASHBOARD_DIR / "static"
TEMPLATES_DIR = DASHBOARD_DIR / "templates"
CONTRACTS_DIR = PROJECT_ROOT / "contracts"

if load_dotenv is not None:
    load_dotenv(PROJECT_ROOT / ".env")


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


class Settings:
    """Lecture paresseuse de l'environnement (réévaluée à l'instanciation)."""

    def __init__(self) -> None:
        self.app_name = "HackCure — Hospital Copilot"
        self.version = "2.0.0"
        self.log_level = os.getenv("LOG_LEVEL", "INFO")

        # Base de données : SQLite par défaut, SQL Server si DATABASE_URL est défini
        self.database_url = os.getenv("DATABASE_URL") or f"sqlite:///{(DASHBOARD_DIR / 'clinic.db').as_posix()}"
        self.seed_on_startup = _bool("SEED_ON_STARTUP", True)

        # Auth
        self.jwt_secret = os.getenv("JWT_SECRET", "hackcure-dev-secret-change-me")
        self.jwt_algorithm = "HS256"
        self.jwt_expire_minutes = _int("JWT_EXPIRE_MINUTES", 12 * 60)
        self.auth_required = _bool("AUTH_REQUIRED", True)
        self.cookie_name = "hackcure_token"
        self.demo_password = os.getenv("DEMO_PASSWORD", "hackcure2026")

        # LLM
        self.llm_provider = os.getenv("LLM_PROVIDER", "mock").lower()
        self.llm_model = os.getenv("LLM_MODEL", "claude-sonnet-5-5")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.llm_timeout_s = _float("LLM_TIMEOUT_S", 20.0)
        if self.llm_provider == "anthropic" and not self.anthropic_api_key:
            self.llm_provider = "mock"

        # MQTT (optionnel)
        self.mqtt_enabled = _bool("MQTT_ENABLED", True)
        self.mqtt_host = os.getenv("MQTT_HOST", "localhost")
        self.mqtt_port = _int("MQTT_PORT", 1883)
        self.mqtt_prefix = os.getenv("MQTT_PREFIX", "hackcure")

        # Telegram (désactivé sans jeton)
        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

        # Simulateur embarqué (appareils + chambres virtuelles dans le serveur)
        self.embedded_sim = _bool("EMBEDDED_SIM", True)
        self.sim_speed = _float("SIM_SPEED", 1.0)

        # Agents
        self.agents_enabled = _bool("AGENTS_ENABLED", True)
        # Délais FollowUp en secondes (valeurs « simulées » courtes pour la démo)
        self.followup_recheck_s = _float("FOLLOWUP_RECHECK_S", 120.0)
        self.escalation_critical_s = _float("ESCALATION_CRITICAL_S", 120.0)
        self.escalation_high_s = _float("ESCALATION_HIGH_S", 600.0)
        self.escalation_medium_s = _float("ESCALATION_MEDIUM_S", 1800.0)

    @property
    def telegram_enabled(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_chat_id)

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


settings = Settings()
