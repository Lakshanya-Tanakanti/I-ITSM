"""T29 and the remaining behaviour: notes, information requests, feedback, administration."""


def _tech(ctx, inc):
    return ctx.tech(inc["assigned_technician"]["full_name"].lower().replace(" ", "."))


def _resolved(ctx):
    inc = ctx.create_incident()["incident"]
    tech = _tech(ctx, inc)
    ctx.transition(inc["number"], tech, "ACKNOWLEDGED")
    ctx.transition(inc["number"], tech, "IN_PROGRESS")
    ctx.transition(inc["number"], tech, "RESOLVED", resolution_summary="Fixed", root_cause="Cause")
    return inc, tech


# --------------------------------------------------------------------------- feedback (T29)
def test_t29_employee_rates_own_resolved_incident_and_others_are_blocked(ctx):
    inc, _ = _resolved(ctx)
    n = inc["number"]
    emp = ctx.employee("rahul.verma")
    r = ctx.client.post(f"/api/incidents/{n}/feedback", headers=emp, json={"rating": 5, "comment": "Great work"})
    assert r.status_code == 201 and r.json()["rating"] == 5
    detail = ctx.client.get(f"/api/incidents/{n}", headers=emp).json()
    assert detail["feedback"]["rating"] == 5 and detail["permissions"]["can_give_feedback"] is False
    assert ctx.client.post(f"/api/incidents/{n}/feedback", headers=emp, json={"rating": 1}).status_code == 409  # only once
    assert ctx.client.post(f"/api/incidents/{n}/feedback", headers=ctx.employee("sneha.iyer"), json={"rating": 1}).status_code == 403
    assert ctx.client.post(f"/api/incidents/{n}/feedback", headers=ctx.admin(), json={"rating": 1}).status_code == 403
    ov = ctx.client.get("/api/reports/overview", headers=ctx.admin()).json()
    assert ov["avg_feedback_rating"] == 5.0


def test_feedback_validation_and_timing(ctx):
    inc = ctx.create_incident()["incident"]
    emp = ctx.employee()
    assert ctx.client.post(f"/api/incidents/{inc['number']}/feedback", headers=emp, json={"rating": 4}).status_code == 409  # not resolved yet
    inc2, _ = _resolved(ctx)
    for bad in (0, 6, "five"):
        assert ctx.client.post(f"/api/incidents/{inc2['number']}/feedback", headers=emp, json={"rating": bad}).status_code == 422


# --------------------------------------------------------------------------- notes and information requests
def test_information_request_and_reply_flow(ctx):
    inc = ctx.create_incident()["incident"]
    n = inc["number"]
    tech, emp = _tech(ctx, inc), ctx.employee()
    r = ctx.client.post(f"/api/incidents/{n}/notes", headers=tech, json={"note_type": "INFO_REQUEST", "body": "Which browser do you use?"})
    assert r.status_code == 201 and r.json()["is_internal"] is False
    detail = ctx.client.get(f"/api/incidents/{n}", headers=emp).json()
    assert detail["awaiting_info"] is True
    dash = ctx.client.get("/api/dashboard", headers=emp).json()
    assert [i["number"] for i in dash["pending_info_requests"]] == [n]
    assert any("More information needed" in x["subject"] for x in ctx.client.get("/api/notifications", headers=emp).json()["items"])
    r = ctx.client.post(f"/api/incidents/{n}/notes", headers=emp, json={"note_type": "INFO_REPLY", "body": "Firefox on Windows"})
    assert r.status_code == 201
    assert ctx.client.get(f"/api/incidents/{n}", headers=emp).json()["awaiting_info"] is False
    assert any("Requester added information" in x["subject"] for x in ctx.client.get("/api/notifications", headers=tech).json()["items"])


def test_internal_notes_are_hidden_from_the_reporter(ctx):
    inc = ctx.create_incident()["incident"]
    n = inc["number"]
    tech, emp = _tech(ctx, inc), ctx.employee()
    ctx.client.post(f"/api/incidents/{n}/notes", headers=tech, json={"note_type": "INVESTIGATION", "body": "Checked logs, secret details here"})
    ctx.client.post(f"/api/incidents/{n}/notes", headers=tech, json={"note_type": "COMMENT", "body": "We are on it"})
    ctx.client.post(f"/api/incidents/{n}/notes", headers=emp, json={"note_type": "ADDITIONAL_INFO", "body": "It also fails on mobile"})
    seen_by_emp = ctx.client.get(f"/api/incidents/{n}/notes", headers=emp).json()
    assert [x["body"] for x in seen_by_emp] == ["We are on it", "It also fails on mobile"]
    assert "secret" not in str(seen_by_emp)
    seen_by_tech = ctx.client.get(f"/api/incidents/{n}/notes", headers=tech).json()
    assert len(seen_by_tech) == 3 and seen_by_tech[0]["is_internal"] is True
    # internal note text is never copied into the employee-visible timeline
    tl = ctx.client.get(f"/api/incidents/{n}/timeline", headers=emp).json()
    assert "secret" not in str(tl)


def test_note_permissions_and_validation(ctx):
    inc = ctx.create_incident()["incident"]
    n = inc["number"]
    tech, emp = _tech(ctx, inc), ctx.employee()
    assert ctx.client.post(f"/api/incidents/{n}/notes", headers=emp, json={"note_type": "INVESTIGATION", "body": "I am a hacker"}).status_code == 403
    assert ctx.client.post(f"/api/incidents/{n}/notes", headers=emp, json={"note_type": "INFO_REQUEST", "body": "Asking myself"}).status_code == 403
    assert ctx.client.post(f"/api/incidents/{n}/notes", headers=tech, json={"note_type": "INFO_REPLY", "body": "Answering myself"}).status_code == 403
    assert ctx.client.post(f"/api/incidents/{n}/notes", headers=tech, json={"note_type": "COMMENT", "body": "   "}).status_code == 422
    assert ctx.client.post(f"/api/incidents/{n}/notes", headers=tech, json={"note_type": "NOPE", "body": "x"}).status_code == 422
    assert ctx.client.post(f"/api/incidents/{n}/notes", headers=ctx.employee("sneha.iyer"), json={"note_type": "ADDITIONAL_INFO", "body": "Not mine"}).status_code == 403


def test_closed_incidents_are_read_only(ctx):
    inc, tech = _resolved(ctx)
    n, emp = inc["number"], ctx.employee()
    ctx.transition(n, emp, "VERIFIED")
    ctx.transition(n, emp, "CLOSED")
    assert ctx.client.post(f"/api/incidents/{n}/notes", headers=tech, json={"note_type": "COMMENT", "body": "late"}).status_code == 409
    assert ctx.client.patch(f"/api/incidents/{n}", headers=ctx.admin(), json={"impact": 1}).status_code == 409
    assert ctx.client.patch(f"/api/incidents/{n}", headers=emp, json={"title": "A different title"}).status_code == 409


def test_incident_update_rules(ctx):
    inc = ctx.create_incident()["incident"]
    n, emp, admin, tech = inc["number"], ctx.employee(), ctx.admin(), _tech(ctx, inc)
    assert ctx.client.patch(f"/api/incidents/{n}", headers=emp, json={}).status_code == 422
    r = ctx.client.patch(f"/api/incidents/{n}", headers=emp, json={"title": "Payment page unavailable for all", "affected_users": 250})
    assert r.status_code == 200 and r.json()["affected_users"] == 250
    assert ctx.client.patch(f"/api/incidents/{n}", headers=tech, json={"title": "Technician rewrote it"}).status_code == 403
    r = ctx.client.patch(f"/api/incidents/{n}", headers=tech, json={"category_id": ctx.category_id("Network")})
    assert r.status_code == 200 and r.json()["category"]["name"] == "Network" and r.json()["category_source"] == "MANUAL"
    assert ctx.client.patch(f"/api/incidents/{n}", headers=emp, json={"category_id": ctx.category_id("Cloud")}).status_code == 403
    r = ctx.client.patch(f"/api/incidents/{n}", headers=admin, json={"service_id": ctx.service_id("Printing")})
    assert r.status_code == 200 and r.json()["business_criticality"] == 1 and r.json()["service"]["name"] == "Printing"
    r = ctx.client.patch(f"/api/incidents/{n}", headers=admin, json={"business_criticality": 5})
    assert r.json()["criticality_overridden"] is True and r.json()["priority"] == "P1"


# --------------------------------------------------------------------------- administration
def test_category_service_policy_and_team_management(ctx):
    admin = ctx.admin()
    c = ctx.client
    cat = c.post("/api/categories", headers=admin, json={"name": "Telephony", "description": "Phones", "keywords": "Phone, phone, Voicemail"})
    assert cat.status_code == 201 and cat.json()["keywords"] == "phone, voicemail"
    assert c.post("/api/categories", headers=admin, json={"name": "telephony"}).status_code == 409
    assert c.patch(f"/api/categories/{cat.json()['id']}", headers=admin, json={"is_active": False}).json()["is_active"] is False
    assert "Telephony" not in [x["name"] for x in c.get("/api/categories", headers=ctx.employee()).json()]
    assert "Telephony" in [x["name"] for x in c.get("/api/categories", headers=admin).json()]

    svc = c.post("/api/services", headers=admin, json={"name": "VPN", "business_criticality": 4})
    assert svc.status_code == 201 and c.post("/api/services", headers=admin, json={"name": "vpn", "business_criticality": 1}).status_code == 409
    assert c.post("/api/services", headers=admin, json={"name": "Bad", "business_criticality": 9}).status_code == 422
    c.patch(f"/api/services/{svc.json()['id']}", headers=admin, json={"is_active": False})
    r = c.post("/api/incidents", headers=ctx.employee(), json={"title": "VPN does not connect", "description": "VPN will not connect.", "service_id": svc.json()["id"], "impact": 2, "urgency": 2})
    assert r.status_code == 404

    pol = c.post("/api/sla-policies", headers=admin, json={"name": "VPN P2", "priority": "P2", "service_id": svc.json()["id"], "response_minutes": 5, "resolution_minutes": 60})
    assert pol.status_code == 201 and pol.json()["service_name"] == "VPN"
    assert c.post("/api/sla-policies", headers=admin, json={"name": "Bad", "priority": "P2", "response_minutes": 60, "resolution_minutes": 10}).status_code == 422
    assert c.post("/api/sla-policies", headers=admin, json={"name": "Bad", "priority": "P9", "response_minutes": 1, "resolution_minutes": 10}).status_code == 422
    assert c.patch(f"/api/sla-policies/{pol.json()['id']}", headers=admin, json={"response_minutes": 7}).json()["response_minutes"] == 7
    assert c.patch("/api/sla-policies/999", headers=admin, json={"response_minutes": 7}).status_code == 404

    team = c.post("/api/teams", headers=admin, json={"name": "Security Ops", "lead_id": ctx.user_id("pooja.desai")})
    assert team.status_code == 201 and team.json()["lead_name"] == "Pooja Desai"
    assert c.post("/api/teams", headers=admin, json={"name": "Bad lead", "lead_id": ctx.user_id("rahul.verma")}).status_code == 422
    assert c.patch(f"/api/teams/{team.json()['id']}", headers=admin, json={"is_active": False}).json()["is_active"] is False
    assert len(c.get("/api/teams", headers=admin).json()) == 3


def test_user_management(ctx):
    admin = ctx.admin()
    c = ctx.client
    r = c.post("/api/users", headers=admin, json={"full_name": "Tess Tech", "email": "tess@iitsm.example.com", "password": "Secret123", "role": "TECHNICIAN"})
    assert r.status_code == 201 and r.json()["employee_code"].startswith("TECH-")
    uid = r.json()["id"]
    assert c.post("/api/users", headers=admin, json={"full_name": "Dup", "email": "TESS@iitsm.example.com", "password": "Secret123", "role": "EMPLOYEE"}).status_code == 409
    r = c.put(f"/api/users/{uid}/technician-profile", headers=admin, json={
        "team_id": 1, "experience_years": 3, "workload_limit": 2, "skills": [{"category_id": ctx.category_id("Network"), "proficiency": 4}]})
    p = r.json()["technician_profile"]
    assert r.status_code == 200 and p["experience_years"] == 3 and p["workload_limit"] == 2 and p["skills"][0]["category_name"] == "Network"
    assert c.put(f"/api/users/{uid}/technician-profile", headers=admin, json={"skills": [{"category_id": 1, "proficiency": 9}]}).status_code == 422
    assert c.put(f"/api/users/{uid}/technician-profile", headers=admin, json={"skills": [{"category_id": 999, "proficiency": 3}]}).status_code == 422
    assert c.put(f"/api/users/{ctx.user_id('rahul.verma')}/technician-profile", headers=admin, json={"is_available": False}).status_code == 422
    assert [u["full_name"] for u in c.get("/api/users?role=TECHNICIAN&q=tess", headers=admin).json()] == ["Tess Tech"]
    assert len(c.get("/api/users?role=TECHNICIAN", headers=admin).json()) == 6
    assert c.patch(f"/api/users/{uid}", headers=admin, json={"role": "EMPLOYEE"}).json()["role"] == "EMPLOYEE"
    me = c.get("/api/auth/me", headers=admin).json()["id"]
    assert c.post(f"/api/users/{me}/deactivate", headers=admin).status_code == 409  # cannot lock yourself out
    assert c.patch(f"/api/users/{me}", headers=admin, json={"role": "EMPLOYEE"}).status_code == 409
    assert c.post(f"/api/users/{uid}/deactivate", headers=admin).status_code == 200
    assert c.post(f"/api/users/{uid}/deactivate", headers=admin).status_code == 409
    assert c.patch(f"/api/users/{uid}", headers=admin, json={"is_active": True}).json()["is_active"] is True


def test_technician_availability_and_workload_views(ctx):
    inc = ctx.create_incident()["incident"]
    tech = _tech(ctx, inc)
    r = ctx.client.patch("/api/technicians/me/availability", headers=tech, json={"is_available": False})
    assert r.status_code == 200 and r.json()["technician_profile"]["is_available"] is False
    mine = ctx.client.get("/api/technicians/workload", headers=tech).json()
    assert len(mine) == 1 and mine[0]["active_incidents"] == 1 and mine[0]["is_available"] is False
    assert len(ctx.client.get("/api/technicians/workload", headers=ctx.admin()).json()) == 5
    assert ctx.client.patch("/api/technicians/me/availability", headers=ctx.employee(), json={"is_available": False}).status_code == 403
    assert ctx.client.get("/api/technicians/workload", headers=ctx.employee()).status_code == 403
    # unavailable technicians are skipped by automatic assignment
    second = ctx.create_incident(title="Payment failing again", description="Payments fail again for many customers.")["incident"]
    assert second["assigned_technician"]["id"] != inc["assigned_technician"]["id"]


def test_error_responses_are_safe_and_consistent(ctx):
    r = ctx.client.get("/api/incidents/INC-9999", headers=ctx.admin())
    assert r.json().keys() >= {"detail", "code"} and "Traceback" not in r.text
    r = ctx.client.get("/api/nope", headers=ctx.admin())
    assert r.status_code == 404 and r.json()["code"] == "HTTP_ERROR"
    r = ctx.client.post("/api/auth/login", content="not json", headers={"Content-Type": "application/json"})
    assert r.status_code == 422
