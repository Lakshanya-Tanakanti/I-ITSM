"""T16 T17 T18 T19: SLA deadlines, warnings, breaches, uniqueness, escalation."""
from datetime import timedelta

from app.domain.enums import Priority
from app.models import AuditLog, SlaViolation


def run_check(ctx):
    r = ctx.client.post("/api/sla/run-check", headers=ctx.admin())
    assert r.status_code == 200, r.text
    return r.json()


def audit_actions(ctx, number=None):
    c, s = ctx.container()
    try:
        rows = s.query(AuditLog).all()
        if number:
            inc = c.repos.incidents.get_by_number(number)
            rows = [r for r in rows if r.incident_id == inc.id]
        return [r.action for r in rows]
    finally:
        s.close()


def violations(ctx):
    c, s = ctx.container()
    try:
        return [(v.incident_id, v.sla_type.value) for v in s.query(SlaViolation).all()]
    finally:
        s.close()


def test_t16_p1_incident_gets_5_and_30_minute_deadlines(ctx):
    inc = ctx.create_incident(service_id=ctx.service_id("Single Sign-On"), impact=4, urgency=5,
                              title="Single sign on is down", description="Nobody can sign in through SSO.")["incident"]
    assert inc["priority"] == "P1"
    assert inc["response_deadline"].startswith("2026-01-15T09:05")
    assert inc["resolution_deadline"].startswith("2026-01-15T09:30")
    assert inc["sla"]["response"]["target_minutes"] == 5 and inc["sla"]["resolution"]["target_minutes"] == 30


def test_all_priorities_use_the_specified_targets(ctx):
    cases = {  # impact, urgency, service (criticality) -> priority, response, resolution
        "Payment Gateway": ((4, 5), "P1", 5, 30),
        "Campus Wi-Fi": ((3, 3), "P2", 15, 120),       # 3*3*3 = 27
        "Library System": ((3, 3), "P3", 60, 480),     # 18
        "Printing": ((1, 2), "P4", 240, 1440),         # 2
    }
    for svc, ((i, u), prio, resp, resol) in cases.items():
        inc = ctx.create_incident(service_id=ctx.service_id(svc), impact=i, urgency=u,
                                  title=f"Issue with {svc}", description="Something is wrong with this service.")["incident"]
        assert inc["priority"] == prio, svc
        assert (inc["sla"]["response"]["target_minutes"], inc["sla"]["resolution"]["target_minutes"]) == (resp, resol)


def test_service_specific_policy_overrides_the_standard_one(ctx):
    inc = ctx.create_incident(service_id=ctx.service_id("Student ERP"), impact=3, urgency=3,
                              title="ERP portal is slow", description="Pages take a minute to load for everyone.")["incident"]
    assert inc["priority"] == "P2"
    assert inc["sla"]["policy_name"] == "Student ERP stricter P2"
    assert inc["sla"]["response"]["target_minutes"] == 10 and inc["sla"]["resolution"]["target_minutes"] == 90


def test_missing_sla_policy_blocks_creation_without_side_effects(ctx):
    admin = ctx.admin()
    policies = ctx.client.get("/api/sla-policies", headers=admin).json()
    for p in policies:
        if p["priority"] == "P1":
            ctx.client.patch(f"/api/sla-policies/{p['id']}", headers=admin, json={"is_active": False})
    r = ctx.client.post("/api/incidents", headers=ctx.employee(), json={
        "title": "Payment is down again", "description": "Payments are failing for everyone.",
        "service_id": ctx.service_id("Payment Gateway"), "impact": 4, "urgency": 5})
    assert r.status_code == 422 and r.json()["code"] == "MISSING_SLA_CONFIGURATION"
    assert ctx.client.get("/api/incidents", headers=admin).json()["total"] == 0


def test_t17_warning_is_generated_once_at_75_percent(ctx):
    inc = ctx.create_incident()["incident"]  # P1: respond within 5 minutes
    ctx.clock.advance(minutes=3)  # 60% -> nothing yet
    assert run_check(ctx)["warnings"] == 0
    ctx.clock.advance(seconds=45)  # 75%
    assert run_check(ctx)["warnings"] == 1
    assert run_check(ctx)["warnings"] == 0
    ctx.clock.advance(seconds=10)
    assert run_check(ctx)["warnings"] == 0
    assert audit_actions(ctx, inc["number"]).count("SLA_WARNING") == 1
    assert ctx.client.get(f"/api/incidents/{inc['number']}", headers=ctx.admin()).json()["sla_status"] == "AT_RISK"
    notes = ctx.client.get("/api/notifications", headers=ctx.admin()).json()["items"]
    assert any("SLA warning" in n["subject"] for n in notes)


def test_t18_response_breach_records_exactly_one_violation(ctx):
    inc = ctx.create_incident()["incident"]
    ctx.clock.advance(minutes=6)
    summary = run_check(ctx)
    assert summary["breaches"] == 1
    assert [v for v in violations(ctx)] == [(1, "RESPONSE")]
    detail = ctx.client.get(f"/api/incidents/{inc['number']}", headers=ctx.admin()).json()
    assert detail["sla_status"] == "BREACHED" and detail["sla"]["response"]["state"] == "BREACHED"
    listing = ctx.client.get("/api/sla/violations", headers=ctx.admin()).json()
    assert len(listing) == 1 and listing[0]["sla_type"] == "RESPONSE" and listing[0]["late_minutes"] >= 1


def test_t19_repeated_monitor_runs_never_duplicate_violations(ctx):
    ctx.create_incident()
    ctx.clock.advance(minutes=40)  # both response (5) and resolution (30) deadlines are gone
    for _ in range(5):
        run_check(ctx)
        ctx.clock.advance(minutes=1)
    assert sorted(violations(ctx)) == [(1, "RESOLUTION"), (1, "RESPONSE")]
    assert audit_actions(ctx).count("SLA_BREACHED") == 2


def test_late_acknowledgement_is_recorded_even_when_monitor_did_not_run(ctx):
    inc = ctx.create_incident()["incident"]
    tech = ctx.tech(inc["assigned_technician"]["full_name"].lower().replace(" ", "."))
    ctx.clock.advance(minutes=8)
    r = ctx.transition(inc["number"], tech, "ACKNOWLEDGED")
    assert r.status_code == 200 and r.json()["sla"]["response"]["state"] == "BREACHED"
    assert violations(ctx) == [(1, "RESPONSE")]
    run_check(ctx)
    assert violations(ctx) == [(1, "RESPONSE")]


def test_resolution_in_time_is_met_and_late_resolution_is_breached(ctx):
    a = ctx.create_incident()["incident"]
    tech = ctx.tech(a["assigned_technician"]["full_name"].lower().replace(" ", "."))
    ctx.clock.advance(minutes=2)
    ctx.transition(a["number"], tech, "ACKNOWLEDGED")
    ctx.transition(a["number"], tech, "IN_PROGRESS")
    ctx.clock.advance(minutes=10)
    r = ctx.transition(a["number"], tech, "RESOLVED", resolution_summary="Fixed", root_cause="Bug").json()
    assert r["sla_status"] == "MET" and r["sla"]["overall"] == "MET"
    assert violations(ctx) == []
    # second incident resolved late
    b = ctx.create_incident(title="Payment failing a second time", description="Customers cannot pay at checkout.")["incident"]
    techb = ctx.tech(b["assigned_technician"]["full_name"].lower().replace(" ", "."))
    ctx.clock.advance(minutes=1)
    ctx.transition(b["number"], techb, "ACKNOWLEDGED")
    ctx.transition(b["number"], techb, "IN_PROGRESS")
    ctx.clock.advance(minutes=45)
    r = ctx.transition(b["number"], techb, "RESOLVED", resolution_summary="Fixed late", root_cause="Slow work").json()
    assert r["sla_status"] == "BREACHED"
    assert (2, "RESOLUTION") in violations(ctx)


def test_resolution_warning_after_acknowledgement(ctx):
    inc = ctx.create_incident()["incident"]
    tech = ctx.tech(inc["assigned_technician"]["full_name"].lower().replace(" ", "."))
    ctx.clock.advance(minutes=1)
    ctx.transition(inc["number"], tech, "ACKNOWLEDGED")
    ctx.clock.advance(minutes=22)  # 23 of 30 minutes = 76%
    assert run_check(ctx)["warnings"] == 1
    assert ctx.client.get(f"/api/incidents/{inc['number']}", headers=ctx.admin()).json()["sla_status"] == "AT_RISK"
    at_risk = ctx.client.get("/api/sla/at-risk", headers=ctx.admin()).json()
    assert [i["number"] for i in at_risk] == [inc["number"]]


def test_escalation_chain_for_unacknowledged_critical_incident(ctx):
    inc = ctx.create_incident()["incident"]
    n = inc["number"]
    admin = ctx.admin()
    level = lambda: ctx.client.get(f"/api/incidents/{n}", headers=admin).json()["escalation_level"]
    ctx.clock.advance(minutes=4)
    run_check(ctx)
    assert level() == 0
    ctx.clock.advance(minutes=2)
    assert run_check(ctx)["escalations"] == 1 and level() == 1
    assert run_check(ctx)["escalations"] == 0
    ctx.clock.advance(minutes=5)
    run_check(ctx)
    assert level() == 2
    ctx.clock.advance(minutes=5)
    run_check(ctx)
    ctx.clock.advance(minutes=5)
    run_check(ctx)
    assert level() == 3  # IT Manager is the last level
    tl = ctx.client.get(f"/api/incidents/{n}/timeline", headers=admin).json()
    names = [e["description"] for e in tl if e["action"] == "INCIDENT_ESCALATED"]
    assert len(names) == 3 and "Team Lead" in names[0] and "System Administrator" in names[1] and "IT Manager" in names[2]


def test_acknowledged_incident_is_not_escalated_and_low_priority_never_escalates(ctx):
    inc = ctx.create_incident(service_id=ctx.service_id("Printing"), impact=1, urgency=1,
                              title="Printer paper tray empty", description="The tray keeps showing empty.")["incident"]
    ctx.clock.advance(minutes=600)
    assert run_check(ctx)["escalations"] == 0
    assert ctx.client.get(f"/api/incidents/{inc['number']}", headers=ctx.admin()).json()["escalation_level"] == 0


def test_escalation_can_be_switched_off(ctx):
    ctx.client.patch("/api/settings", headers=ctx.admin(), json={"escalation_enabled": False})
    ctx.create_incident()
    ctx.clock.advance(minutes=20)
    assert run_check(ctx)["escalations"] == 0


def test_monitor_object_runs_a_check_on_demand(ctx):
    from app.services.sla_monitor import SlaMonitor
    ctx.create_incident()
    ctx.clock.advance(minutes=6)
    monitor = SlaMonitor(ctx.factory, ctx.clock, ctx.settings, 60)
    summary = monitor.run_once()
    assert summary["breaches"] == 1 and monitor.runs == 1
    monitor.start()
    assert monitor.is_running
    monitor.stop()
    assert not monitor.is_running
    status = ctx.client.get("/api/sla/monitor", headers=ctx.admin()).json()
    assert "running" in status


def test_resolved_incident_stops_the_clock(ctx):
    inc = ctx.create_incident()["incident"]
    tech = ctx.tech(inc["assigned_technician"]["full_name"].lower().replace(" ", "."))
    ctx.clock.advance(minutes=1)
    ctx.transition(inc["number"], tech, "ACKNOWLEDGED")
    ctx.transition(inc["number"], tech, "IN_PROGRESS")
    ctx.transition(inc["number"], tech, "RESOLVED", resolution_summary="done", root_cause="cause")
    ctx.clock.advance(minutes=600)
    assert run_check(ctx)["breaches"] == 0 and violations(ctx) == []
