"""T04 and role based access control."""


def test_t04_employee_cannot_read_another_employees_incident(ctx):
    inc = ctx.create_incident(ctx.employee("rahul.verma"))["incident"]
    other = ctx.employee("sneha.iyer")
    r = ctx.client.get(f"/api/incidents/{inc['number']}", headers=other)
    assert r.status_code == 403
    assert inc["title"] not in r.text
    for sub in ("notes", "timeline"):
        assert ctx.client.get(f"/api/incidents/{inc['number']}/{sub}", headers=other).status_code == 403


def test_employee_list_only_contains_own_incidents(ctx):
    ctx.create_incident(ctx.employee("rahul.verma"), title="Rahul printer problem now")
    ctx.create_incident(ctx.employee("sneha.iyer"), title="Sneha wifi problem now", service_id=ctx.service_id("Campus Wi-Fi"),
                        impact=2, urgency=2)
    r = ctx.client.get("/api/incidents", headers=ctx.employee("rahul.verma")).json()
    assert r["total"] == 1 and r["items"][0]["reporter"]["full_name"] == "Rahul Verma"
    assert ctx.client.get("/api/incidents", headers=ctx.admin()).json()["total"] == 2


def test_technician_only_sees_assigned_incidents(ctx):
    inc = ctx.create_incident()["incident"]
    assigned = inc["assigned_technician"]["full_name"]
    local = assigned.lower().replace(" ", ".")
    assert ctx.client.get(f"/api/incidents/{inc['number']}", headers=ctx.tech(local)).status_code == 200
    other = "vikram.singh" if local != "vikram.singh" else "arjun.kapoor"
    assert ctx.client.get(f"/api/incidents/{inc['number']}", headers=ctx.tech(other)).status_code == 403
    assert ctx.client.get("/api/incidents", headers=ctx.tech(other)).json()["total"] == 0
    assert ctx.client.get("/api/incidents", headers=ctx.tech(local)).json()["total"] == 1


def test_admin_only_endpoints_reject_other_roles(ctx):
    emp, tech = ctx.employee(), ctx.tech()
    admin_gets = ["/api/users", "/api/audit-logs", "/api/reports/overview", "/api/sla-policies", "/api/settings",
                  "/api/teams", "/api/admin/email-outbox", "/api/sla/violations", "/api/sla/at-risk"]
    for url in admin_gets:
        assert ctx.client.get(url, headers=emp).status_code == 403, url
        assert ctx.client.get(url, headers=tech).status_code == 403, url
        assert ctx.client.get(url, headers=ctx.admin()).status_code == 200, url


def test_admin_write_endpoints_reject_non_admins(ctx):
    emp = ctx.employee()
    assert ctx.client.post("/api/categories", headers=emp, json={"name": "Hacked"}).status_code == 403
    assert ctx.client.post("/api/services", headers=emp, json={"name": "Hacked", "business_criticality": 1}).status_code == 403
    assert ctx.client.patch("/api/settings", headers=emp, json={"auto_assign": False}).status_code == 403
    assert ctx.client.post("/api/users", headers=emp, json={
        "full_name": "Bad Actor", "email": "bad@iitsm.example.com", "password": "Secret123", "role": "ADMIN"}).status_code == 403
    assert ctx.client.post("/api/sla/run-check", headers=emp).status_code == 403


def test_technician_cannot_report_incident(ctx):
    r = ctx.client.post("/api/incidents", headers=ctx.tech(), json={
        "title": "Tech report attempt", "description": "Technicians should not report incidents.",
        "service_id": ctx.service_id("Printing"), "impact": 1, "urgency": 1})
    assert r.status_code == 403


def test_employee_cannot_assign_or_use_recommendations(ctx):
    inc = ctx.create_incident()["incident"]
    emp = ctx.employee()
    tech_id = ctx.user_id("vikram.singh")
    assert ctx.client.post(f"/api/incidents/{inc['number']}/assign", headers=emp, json={"technician_id": tech_id}).status_code == 403
    assert ctx.client.get(f"/api/incidents/{inc['number']}/recommendations", headers=emp).status_code == 403
    assert ctx.client.get(f"/api/incidents/{inc['number']}/related", headers=emp).status_code == 403


def test_non_admin_cannot_change_priority_fields(ctx):
    inc = ctx.create_incident()["incident"]
    r = ctx.client.patch(f"/api/incidents/{inc['number']}", headers=ctx.employee(), json={"impact": 1})
    assert r.status_code == 403
    r = ctx.client.patch(f"/api/incidents/{inc['number']}", headers=ctx.employee(), json={"description": "Updated description for clarity."})
    assert r.status_code == 200


def test_users_can_only_view_or_edit_themselves(ctx):
    emp = ctx.employee("rahul.verma")
    me = ctx.user_id("rahul.verma")
    other = ctx.user_id("sneha.iyer")
    assert ctx.client.get(f"/api/users/{me}", headers=emp).status_code == 200
    assert ctx.client.get(f"/api/users/{other}", headers=emp).status_code == 403
    assert ctx.client.patch(f"/api/users/{other}", headers=emp, json={"full_name": "Hijack"}).status_code == 403
    assert ctx.client.patch(f"/api/users/{me}", headers=emp, json={"role": "ADMIN"}).status_code == 403


def test_unknown_incident_returns_404(ctx):
    assert ctx.client.get("/api/incidents/INC-9999", headers=ctx.admin()).status_code == 404
    assert ctx.client.get("/api/incidents/INC-9999", headers=ctx.employee()).status_code == 404
