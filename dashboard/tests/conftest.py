"""Fixtures pytest : client HTTP + WebSocket sur l'application FastAPI (base SQLite temporaire)."""
import os
import sys
from pathlib import Path

import pytest

DASHBOARD_DIR = Path(__file__).resolve().parent.parent
if str(DASHBOARD_DIR) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_DIR))

# Base de test isolée, auth active (les tests se connectent explicitement)
_TEST_DB = DASHBOARD_DIR / "tests" / "_test_clinic.db"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_TEST_DB.as_posix()}")
os.environ.setdefault("EMBEDDED_SIM", "0")
os.environ.setdefault("MQTT_ENABLED", "0")
os.environ.setdefault("LLM_PROVIDER", "mock")
os.environ.setdefault("FOLLOWUP_RECHECK_S", "0.2")
os.environ.setdefault("ESCALATION_CRITICAL_S", "2")


@pytest.fixture(scope="session")
def app():
    if _TEST_DB.exists():
        try:
            _TEST_DB.unlink()
        except OSError:
            pass
    from app.main import app as fastapi_app
    return fastapi_app


@pytest.fixture(scope="session")
def client(app):
    from fastapi.testclient import TestClient
    with TestClient(app) as c:
        yield c
