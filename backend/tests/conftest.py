"""Shared test fixtures. Every test gets its own in-memory database and a movable clock."""
import os

os.environ.setdefault("BCRYPT_ROUNDS", "4")
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-long-enough-for-hs256")
os.environ.setdefault("SLA_MONITOR_ENABLED", "false")

from dataclasses import dataclass
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.database import init_db, make_engine, make_session_factory
from app.domain.clock import MutableClock
from app.main import create_app
from app.services.container import build_container
from app.utils.seed import (
    ADMIN_PASSWORD, DOMAIN, EMPLOYEE_PASSWORD, TECH_PASSWORD, _create_reference_data,
)

START = datetime(2026, 1, 15, 9, 0, tzinfo=timezone.utc)


@dataclass
class Ctx:
    app: object
    client: TestClient
    factory: object
    clock: MutableClock
    settings: Settings

    # ---- helpers -----------------------------------------------------------------
    def login(self, local: str, password: str) -> dict:
        r = self.client.post("/api/auth/login", json={"email": f"{local}@{DOMAIN}", "password": password})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    def admin(self):
        return self.login("admin", ADMIN_PASSWORD)

    def employee(self, local="rahul.verma"):
        return self.login(local, EMPLOYEE_PASSWORD)

    def tech(self, local="meera.joshi"):
        return self.login(local, TECH_PASSWORD)

    def container(self):
        session = self.factory()
        return build_container(session, self.clock, self.settings), session

    def create_incident(self, headers=None, **overrides):
        body = {"title": "Payment application unavailable", "description": "Users cannot complete payment transactions.",
                "service_id": self.service_id("Payment Gateway"), "impact": 4, "urgency": 5}
        body.update(overrides)
        r = self.client.post("/api/incidents", json=body, headers=headers or self.employee())
        assert r.status_code == 201, r.text
        return r.json()

    def service_id(self, name):
        c, s = self.container()
        try:
            return c.repos.services.get_by_name(name).id
        finally:
            s.close()

    def category_id(self, name):
        c, s = self.container()
        try:
            return c.repos.categories.get_by_name(name).id
        finally:
            s.close()

    def user_id(self, local):
        c, s = self.container()
        try:
            return c.repos.users.get_by_email(f"{local}@{DOMAIN}").id
        finally:
            s.close()

    def transition(self, number, headers, to_status, **payload):
        return self.client.post(f"/api/incidents/{number}/transition", headers=headers,
                                json={"to_status": to_status, **payload})


@pytest.fixture
def ctx():
    engine = make_engine("sqlite://")
    init_db(engine)
    factory = make_session_factory(engine)
    clock = MutableClock(START)
    settings = Settings(sla_monitor_enabled=False, seed_demo_data=False)
    app = create_app(settings=settings, session_factory=factory, clock=clock, start_monitor=False, seed=False)
    session = factory()
    _create_reference_data(build_container(session, clock, settings), clock.now())
    session.close()
    with TestClient(app) as client:
        yield Ctx(app, client, factory, clock, settings)
    engine.dispose()
