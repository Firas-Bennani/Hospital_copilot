"""
Application FastAPI — Hospital Copilot.

Point d'entrée conservé : `cd dashboard && uvicorn server:app --reload --host 0.0.0.0 --port 8000`
(`server.py` importe `app` depuis ce module).
"""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import state
from .config import STATIC_DIR, settings
from .ws import manager

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("hackcure.server")

_background_tasks: list[asyncio.Task] = []


def _import_optional(path: str):
    """Import d'un sous-module de phase ultérieure sans casser le démarrage s'il manque."""
    try:
        import importlib

        return importlib.import_module(path, package=__package__)
    except ModuleNotFoundError as exc:  # pragma: no cover - dépend des phases livrées
        if exc.name and exc.name.startswith("app."):
            return None
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("%s v%s", settings.app_name, settings.version)
    logger.info("Dashboard: http://localhost:8000")
    logger.info("WebSocket: ws://localhost:8000/ws")
    logger.info("DB: %s", settings.database_url.split("@")[-1])
    logger.info("LLM: %s (%s)", settings.llm_provider, settings.llm_model)
    logger.info("=" * 60)

    db = _import_optional(".db")
    if db is not None:
        db.init_db()
        seed = _import_optional(".seed")
        if seed is not None and settings.seed_on_startup:
            seed.seed_all()

    for mod_name, starter in (
        (".ingest.mqtt", "start"),
        (".sim.embedded", "start"),
        (".agents.manager", "start"),
    ):
        mod = _import_optional(mod_name)
        if mod is not None and hasattr(mod, starter):
            try:
                tasks = await getattr(mod, starter)()
                if tasks:
                    _background_tasks.extend(tasks)
            except Exception:  # pragma: no cover
                logger.exception("Démarrage de %s impossible", mod_name)

    try:
        yield
    finally:
        for t in _background_tasks:
            t.cancel()
        for t in _background_tasks:
            try:
                await t
            except (asyncio.CancelledError, Exception):
                pass
        _background_tasks.clear()


def create_app() -> FastAPI:
    app = FastAPI(
        title="HackCure Patient Monitoring",
        description="Privacy-preserving AI patient monitoring with 3D digital twin",
        version=settings.version,
        lifespan=lifespan,
    )

    from .api import demo as demo_api

    app.include_router(demo_api.router)

    # Routeurs des phases suivantes (inclus s'ils existent)
    for name in (
        "auth",
        "patients",
        "rooms",
        "devices",
        "risks",
        "commands",
        "pharmacy",
        "staff",
        "reports",
        "prescriptions",
        "agents",
        "ingest",
        "notifications",
        "scenario",
        "users",
        "kpi",
        "print",
    ):
        mod = _import_optional(f".api.{name}")
        if mod is not None and hasattr(mod, "router"):
            app.include_router(mod.router)

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        role = None
        auth = _import_optional(".auth")
        if auth is not None:
            role = auth.role_from_cookie(websocket.cookies.get(settings.cookie_name))
        await manager.connect(websocket, role)
        try:
            await websocket.send_text(json.dumps(state.init_message(), default=str))
            while True:
                data = await websocket.receive_text()
                try:
                    msg = json.loads(data)
                except json.JSONDecodeError:
                    continue
                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
        except WebSocketDisconnect:
            manager.disconnect(websocket)
        except Exception as e:  # pragma: no cover
            logger.error("WebSocket error: %s", e)
            manager.disconnect(websocket)

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/")
    async def serve_dashboard(request: Request):
        auth = _import_optional(".auth")
        if auth is not None and settings.auth_required and auth.optional_user(request) is None:
            return RedirectResponse(url="/login", status_code=302)
        return FileResponse(str(STATIC_DIR / "index.html"))

    @app.get("/login")
    async def serve_login():
        page = STATIC_DIR / "login.html"
        if page.exists():
            return FileResponse(str(page))
        return FileResponse(str(STATIC_DIR / "index.html"))

    @app.get("/health")
    async def health():
        return JSONResponse(
            {
                "status": "ok",
                "version": settings.version,
                "mode": state.current_mode["mode"],
                "ws_clients": manager.count,
                "llm_provider": settings.llm_provider,
                "mqtt": getattr(_import_optional(".ingest.mqtt"), "status", lambda: "disabled")(),
                "telegram": settings.telegram_enabled,
            }
        )

    return app


app = create_app()
