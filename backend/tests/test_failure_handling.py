"""Database-failure and unexpected-failure handling (brief: "Database failure" scenario).

These tests replace the one-off manual probe used earlier. They check that a failing
database gives a safe JSON error (no SQL, no stack trace), that the transaction is rolled
back so no half-written incident remains, and that /health reports the database as down.
"""
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.observers.audit_observer import AuditObserver
from app.services.incident_service import IncidentService


def _incident_count(ctx) -> int:
    c, s = ctx.container()
    try:
        return s.execute(text("SELECT COUNT(*) FROM incidents")).scalar_one()
    finally:
        s.close()


def _assert_safe(body: dict):
    raw = str(body).lower()
    for leak in ("select", "insert", "traceback", "sqlite", "operationalerror", ".py"):
        assert leak not in raw, f"error body leaks internals: {body}"


def test_real_database_failure_returns_503_without_internals(ctx):
    """A genuine SQLite failure (the incidents table disappears) is reported as 503 DATABASE_ERROR."""
    headers = ctx.admin()
    s = ctx.factory()
    s.execute(text("ALTER TABLE incidents RENAME TO incidents_unavailable"))
    s.commit()
    s.close()
    r = ctx.client.get("/api/incidents", headers=headers)
    assert r.status_code == 503
    assert r.json()["code"] == "DATABASE_ERROR"
    _assert_safe(r.json())


def test_database_failure_during_creation_rolls_back_everything(ctx, monkeypatch):
    """If the audit write fails at database level, the incident is not stored at all."""
    before = _incident_count(ctx)
    headers = ctx.employee()

    def broken(self, event):
        raise OperationalError("INSERT INTO audit_logs", {}, Exception("disk I/O error"))

    monkeypatch.setattr(AuditObserver, "handle", broken)
    body = {"title": "Payment application unavailable", "description": "Users cannot complete payment transactions.",
            "service_id": ctx.service_id("Payment Gateway"), "impact": 4, "urgency": 5}
    r = ctx.client.post("/api/incidents", json=body, headers=headers)
    assert r.status_code == 503
    assert r.json()["code"] == "DATABASE_ERROR"
    _assert_safe(r.json())
    assert _incident_count(ctx) == before


def test_other_database_errors_return_500_database_error(ctx, monkeypatch):
    headers = ctx.admin()

    def broken(self, actor, filters):
        raise SQLAlchemyError("internal mapper failure")

    monkeypatch.setattr(IncidentService, "list_incidents", broken)
    r = ctx.client.get("/api/incidents", headers=headers)
    assert r.status_code == 500
    assert r.json()["code"] == "DATABASE_ERROR"
    _assert_safe(r.json())


def test_integrity_error_returns_409_conflict(ctx, monkeypatch):
    headers = ctx.admin()

    def broken(self, actor, filters):
        raise IntegrityError("INSERT INTO incidents", {}, Exception("UNIQUE constraint failed"))

    monkeypatch.setattr(IncidentService, "list_incidents", broken)
    r = ctx.client.get("/api/incidents", headers=headers)
    assert r.status_code == 409
    assert r.json()["code"] == "CONFLICT"
    _assert_safe(r.json())


def test_health_reports_database_down(ctx, monkeypatch):
    assert ctx.client.get("/health").json()["database"] is True

    def broken(self, *args, **kwargs):
        raise OperationalError("SELECT 1", {}, Exception("unable to open database file"))

    monkeypatch.setattr(Session, "execute", broken)
    r = ctx.client.get("/health")
    assert r.status_code == 200
    assert r.json()["database"] is False
    assert r.json()["status"] == "degraded"


def test_unexpected_error_returns_generic_500(ctx, monkeypatch):
    headers = ctx.admin()

    def broken(self, actor, filters):
        raise RuntimeError("secret internal detail in /srv/app/x.py")

    monkeypatch.setattr(IncidentService, "list_incidents", broken)
    with TestClient(ctx.app, raise_server_exceptions=False) as client:
        r = client.get("/api/incidents", headers=headers)
    assert r.status_code == 500
    assert r.json() == {"detail": "An unexpected error occurred.", "code": "INTERNAL_ERROR"}
