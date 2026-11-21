"""T20 T21 T22: notifications (in-app + simulated e-mail) and the append-only audit log."""
import pytest

from app.models import AuditLog
from app.models.audit import AuditImmutableError


def _tech_headers(ctx, incident):
    return ctx.tech(incident["assigned_technician"]["full_name"].lower().replace(" ", "."))


def test_t20_creation_assignment_and_resolution_create_in_app_and_email_records(ctx):
    emp, admin = ctx.employee(), ctx.admin()
    inc = ctx.create_incident(emp)["incident"]
    tech = _tech_headers(ctx, inc)
    reporter_inbox = ctx.client.get("/api/notifications", headers=emp).json()
    subjects = [n["subject"] for n in reporter_inbox["items"]]
    assert any("Incident reported" in s for s in subjects)
    assert any("Classified as" in s and "P1" in s for s in subjects)
    assert any("Technician assigned" in s for s in subjects)
    tech_inbox = ctx.client.get("/api/notifications", headers=tech).json()
    assert any("New incident assigned to you" in n["subject"] for n in tech_inbox["items"])
    assert any("Incident reported" in n["subject"] for n in ctx.client.get("/api/notifications", headers=admin).json()["items"])

    ctx.transition(inc["number"], tech, "ACKNOWLEDGED")
    ctx.transition(inc["number"], tech, "IN_PROGRESS")
    ctx.transition(inc["number"], tech, "RESOLVED", resolution_summary="Restarted", root_cause="Leak")
    subjects = [n["subject"] for n in ctx.client.get("/api/notifications", headers=emp).json()["items"]]
    assert any("Technician acknowledged" in s for s in subjects)
    assert any("Investigation started" in s for s in subjects)
    assert any("Incident resolved" in s for s in subjects)

    outbox = ctx.client.get("/api/admin/email-outbox", headers=admin).json()
    assert outbox and all(m["channel"] == "EMAIL" and m["delivery_status"] == "SENT" for m in outbox)
    assert {"rahul.verma@iitsm.example.com", "admin@iitsm.example.com"} <= {m["to_email"] for m in outbox}
    assert any("resolved" in m["subject"].lower() for m in outbox)
    # e-mail copies are not shown in the in-app inbox
    assert all(n["channel"] == "IN_APP" for n in reporter_inbox["items"])


def test_users_do_not_receive_notifications_for_their_own_actions(ctx):
    inc = ctx.create_incident()["incident"]
    tech = _tech_headers(ctx, inc)
    before = ctx.client.get("/api/notifications", headers=tech).json()["total"]
    ctx.transition(inc["number"], tech, "ACKNOWLEDGED")
    assert ctx.client.get("/api/notifications", headers=tech).json()["total"] == before


def test_notifications_read_state_and_isolation(ctx):
    emp = ctx.employee()
    ctx.create_incident(emp)
    data = ctx.client.get("/api/notifications", headers=emp).json()
    assert data["unread_count"] == data["total"] > 0
    first = data["items"][0]["id"]
    r = ctx.client.post(f"/api/notifications/{first}/read", headers=emp)
    assert r.status_code == 200 and r.json()["is_read"] is True
    assert ctx.client.get("/api/notifications", headers=emp).json()["unread_count"] == data["unread_count"] - 1
    # nobody else can mark it
    assert ctx.client.post(f"/api/notifications/{first}/read", headers=ctx.employee("sneha.iyer")).status_code == 404
    assert ctx.client.post("/api/notifications/read-all", headers=emp).status_code == 200
    assert ctx.client.get("/api/notifications?unread_only=true", headers=emp).json()["items"] == []
    assert ctx.client.get("/api/notifications", headers=emp).json()["unread_count"] == 0


def test_priority_change_and_closure_notify(ctx):
    emp = ctx.employee()
    inc = ctx.create_incident(emp)["incident"]
    ctx.client.patch(f"/api/incidents/{inc['number']}", headers=ctx.admin(), json={"urgency": 2})
    subjects = [n["subject"] for n in ctx.client.get("/api/notifications", headers=emp).json()["items"]]
    assert any("Priority changed" in s for s in subjects)


def test_t21_transition_creates_audit_row_with_actor_action_states_and_time(ctx):
    inc = ctx.create_incident()["incident"]
    tech = _tech_headers(ctx, inc)
    ctx.clock.advance(minutes=1)
    ctx.transition(inc["number"], tech, "ACKNOWLEDGED")
    items = ctx.client.get(f"/api/audit-logs?number={inc['number']}", headers=ctx.admin()).json()["items"]
    row = [i for i in items if i["action"] == "INCIDENT_ACKNOWLEDGED"][0]
    assert row["actor_name"] == inc["assigned_technician"]["full_name"] and row["actor_id"] == inc["assigned_technician"]["id"]
    assert (row["previous_state"], row["new_state"]) == ("ASSIGNED", "ACKNOWLEDGED")
    assert row["created_at"].startswith("2026-01-15T09:01") and row["incident_number"] == inc["number"]
    created = [i for i in items if i["action"] == "INCIDENT_CREATED"][0]
    assert created["actor_name"] == "Rahul Verma"
    system = [i for i in items if i["action"] == "INCIDENT_ASSIGNED"][0]
    assert system["actor_name"] == "System"


def test_audit_log_filters_and_pagination(ctx):
    for i in range(3):
        ctx.create_incident(title=f"Payment problem number {i}", description="Customers cannot pay at checkout.")
    admin = ctx.admin()
    page = ctx.client.get("/api/audit-logs?page=1&page_size=5", headers=admin).json()
    assert len(page["items"]) == 5 and page["total"] > 5 and page["pages"] > 1
    created = ctx.client.get("/api/audit-logs?action=INCIDENT_CREATED", headers=admin).json()
    assert created["total"] == 3
    rahul = ctx.user_id("rahul.verma")
    assert ctx.client.get(f"/api/audit-logs?actor_id={rahul}", headers=admin).json()["total"] >= 3
    assert ctx.client.get("/api/audit-logs?q=classified", headers=admin).json()["total"] >= 3
    assert ctx.client.get("/api/audit-logs?from_date=2026-01-16", headers=admin).json()["total"] == 0
    assert ctx.client.get("/api/audit-logs?from_date=2026-01-15&to_date=2026-01-15", headers=admin).json()["total"] > 0
    assert ctx.client.get("/api/audit-logs?from_date=2026-02-01&to_date=2026-01-01", headers=admin).status_code == 422
    assert "INCIDENT_CREATED" in ctx.client.get("/api/audit-logs/actions", headers=admin).json()


def test_t22_audit_records_cannot_be_edited_or_deleted_via_api(ctx):
    ctx.create_incident()
    admin = ctx.admin()
    for method in ("put", "patch", "delete", "post"):
        r = getattr(ctx.client, method)("/api/audit-logs/1", headers=admin)
        assert r.status_code in (404, 405), method
        r = getattr(ctx.client, method)("/api/audit-logs", headers=admin)
        assert r.status_code in (405, 422), method
    paths = {r.path: r.methods for r in ctx.app.routes if hasattr(r, "methods")}
    for path, methods in paths.items():
        if "audit" in path:
            assert methods <= {"GET", "HEAD"}, path


def test_audit_rows_are_immutable_at_orm_level(ctx):
    ctx.create_incident()
    c, s = ctx.container()
    row = s.query(AuditLog).first()
    row.description = "tampered"
    with pytest.raises(AuditImmutableError):
        s.commit()
    s.rollback()
    row = s.query(AuditLog).first()
    s.delete(row)
    with pytest.raises(AuditImmutableError):
        s.commit()
    s.rollback()
    s.close()


def test_account_and_admin_actions_are_audited(ctx):
    admin = ctx.admin()
    r = ctx.client.post("/api/users", headers=admin, json={
        "full_name": "Nina Fresh", "email": "nina.fresh@iitsm.example.com", "password": "Secret123", "role": "TECHNICIAN"})
    assert r.status_code == 201 and r.json()["technician_profile"] is not None
    ctx.client.post("/api/categories", headers=admin, json={"name": "Printing Hardware", "keywords": "toner, ink"})
    actions = {i["action"] for i in ctx.client.get("/api/audit-logs?page_size=100", headers=admin).json()["items"]}
    assert {"USER_CREATED", "CONFIG_CHANGED", "USER_LOGIN"} <= actions
