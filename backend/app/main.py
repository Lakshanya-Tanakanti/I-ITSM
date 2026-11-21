"""FastAPI application factory."""
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import Settings, get_settings
from app.database import get_default_engine, get_default_session_factory, init_db, make_engine, make_session_factory
from app.domain.clock import Clock, SystemClock
from app.middleware.errors import register_error_handlers
from app.routes import auth, config as config_routes, incidents, operations, users
from app.services.container import build_container
from app.services.sla_monitor import SlaMonitor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("iitsm")


def create_app(settings: Optional[Settings] = None, session_factory=None, clock: Optional[Clock] = None,
               start_monitor: Optional[bool] = None, seed: Optional[bool] = None) -> FastAPI:
    settings = settings or get_settings()
    clock = clock or SystemClock()
    if session_factory is None:
        engine = get_default_engine()
        session_factory = get_default_session_factory()
    else:
        engine = session_factory.kw["bind"]
    run_monitor = settings.sla_monitor_enabled if start_monitor is None else start_monitor
    run_seed = settings.seed_demo_data if seed is None else seed
    if settings.is_production and settings.uses_default_secret:
        raise RuntimeError("Refusing to start in production with the default SECRET_KEY. Set SECRET_KEY in backend/.env.")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        init_db(engine)
        from app.utils import seed as seeding
        if run_seed:
            seeding.seed_if_empty(session_factory, settings)
        else:
            seeding.bootstrap_if_empty(session_factory, settings)
        # First SLA evaluation straight away, then every N seconds in the background.
        monitor = SlaMonitor(session_factory, clock, settings, settings.sla_monitor_interval_seconds)
        app.state.sla_monitor = monitor
        if run_monitor:
            monitor.start()
        yield
        monitor.stop()

    app = FastAPI(
        title="I-ITSM API",
        description="Intelligent IT Service Management & Incident Resolution System",
        version="1.0.0", lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.session_factory = session_factory
    app.state.clock = clock
    app.state.sla_monitor = None

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin, "http://127.0.0.1:5173", "http://localhost:5173"],
        allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
    )
    register_error_handlers(app)

    prefix = settings.api_prefix
    for module in (auth, users, incidents, config_routes, operations):
        app.include_router(module.router, prefix=prefix)

    @app.get("/health", tags=["Health"])
    def health():
        db_ok = True
        try:
            with session_factory() as s:
                s.execute(text("SELECT 1"))
        except Exception:  # noqa: BLE001
            db_ok = False
        monitor = app.state.sla_monitor
        return {"status": "ok" if db_ok else "degraded", "database": db_ok,
                "sla_monitor_running": bool(monitor and monitor.is_running), "version": "1.0.0"}

    return app


app = create_app()
