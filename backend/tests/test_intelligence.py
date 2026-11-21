"""T24 T25 T26 and the other intelligent features (all rule based and explainable)."""
import pytest

from app.utils.text import jaccard, keyword_hits, tokens


def _tech(ctx, inc):
    return ctx.tech(inc["assigned_technician"]["full_name"].lower().replace(" ", "."))


# --------------------------------------------------------------------------- text helpers
def test_synonyms_and_phrases_map_to_the_same_tokens():
    assert tokens("Payment application unavailable") == tokens("Payment transaction failing") == tokens("Unable to make payment")
    assert tokens("Wi-Fi is not working") == tokens("wifi down")
    assert tokens("Cannot log in to SSO") >= {"login", "fail"}
    assert jaccard(tokens("printer jammed"), tokens("payment failing")) == 0
    assert jaccard(set(), {"a"}) == 0


def test_keyword_matching_rules():
    assert keyword_hits("Wi-Fi is down", "", "wifi") == 2
    assert keyword_hits("Problem", "the printers are broken", "printer") == 1  # plural via prefix
    assert keyword_hits("Problem", "no match here", "network") == 0
    assert keyword_hits("My account is locked out", "", "locked out") == 2   # multi word phrase
    assert keyword_hits("x", "ad hoc request", "ad") == 1                      # short keyword needs exact word
    assert keyword_hits("x", "address book", "ad") == 0


# --------------------------------------------------------------------------- category suggestion
def test_t25_network_keywords_suggest_network_with_reason(ctx):
    r = ctx.client.post("/api/intelligence/suggest-category", headers=ctx.employee(), json={
        "title": "VPN and wifi connection keeps dropping", "description": "The router in building B loses connectivity."})
    assert r.status_code == 200
    s = r.json()["suggestion"]
    assert s["category_name"] == "Network"
    assert {"vpn", "wifi", "router"} <= set(s["matched_keywords"])
    assert "Matched keyword" in s["reason"] and 0 < s["confidence"] < 1


def test_category_suggestion_for_other_categories_and_no_match(ctx):
    h = ctx.employee()
    post = lambda t, d="": ctx.client.post("/api/intelligence/suggest-category", headers=h, json={"title": t, "description": d}).json()
    assert post("Suspicious phishing email received")["suggestion"]["category_name"] == "Security"
    assert post("Cannot reset password, account locked out")["suggestion"]["category_name"] == "Authentication"
    assert post("Laptop battery does not charge")["suggestion"]["category_name"] == "Hardware"
    assert post("Something odd happened", "no clue")["suggestion"] is None


def test_suggested_category_is_used_when_the_reporter_leaves_it_empty(ctx):
    inc = ctx.create_incident(service_id=ctx.service_id("Campus Wi-Fi"), impact=3, urgency=3, title="Wifi router keeps rebooting",
                              description="The wireless router in the hall restarts every hour.")["incident"]
    assert inc["category"]["name"] == "Network" and inc["category_source"] == "AUTO"
    chosen = ctx.create_incident(service_id=ctx.service_id("Campus Wi-Fi"), impact=3, urgency=3, category_id=ctx.category_id("Hardware"),
                                 title="Wifi router keeps rebooting again", description="The wireless router restarts every hour.")["incident"]
    assert chosen["category"]["name"] == "Hardware" and chosen["category_source"] == "USER"
    other = ctx.create_incident(service_id=ctx.service_id("Printing"), impact=1, urgency=1, title="Strange thing happened",
                                description="Nothing specific can be said about it.")["incident"]
    assert other["category"]["name"] == "Application" and other["category_source"] == "DEFAULT"


def test_admin_keyword_changes_alter_suggestions_without_code_changes(ctx):
    admin = ctx.admin()
    cat = ctx.category_id("Hardware")
    ctx.client.patch(f"/api/categories/{cat}", headers=admin, json={"keywords": "projector, whiteboard"})
    r = ctx.client.post("/api/intelligence/suggest-category", headers=ctx.employee(), json={"title": "Projector bulb gone", "description": ""})
    assert r.json()["suggestion"]["category_name"] == "Hardware"
    new = ctx.client.post("/api/categories", headers=admin, json={"name": "Telephony", "keywords": "phone, extension, voicemail"}).json()
    r = ctx.client.post("/api/intelligence/suggest-category", headers=ctx.employee(), json={"title": "Desk phone has no voicemail", "description": ""})
    assert r.json()["suggestion"]["category_name"] == "Telephony" and r.json()["suggestion"]["category_id"] == new["id"]


# --------------------------------------------------------------------------- duplicates
def test_t24_similar_payment_incident_triggers_a_warning_but_is_not_blocked(ctx):
    first = ctx.create_incident(ctx.employee("rahul.verma"), title="Payment application unavailable",
                                description="Users cannot complete payment transactions.")
    assert first["duplicates"] == []
    second = ctx.create_incident(ctx.employee("sneha.iyer"), title="Unable to make payment",
                                 description="Checkout shows an error when I try to pay.")
    assert second["incident"]["number"] != first["incident"]["number"]  # created, not blocked, not merged
    assert second["duplicates"] and second["duplicates"][0]["number"] == first["incident"]["number"]
    d = second["duplicates"][0]
    assert d["similarity"] >= 0.45 and "Same service" in d["reasons"] and any("Shared terms" in r for r in d["reasons"])
    third = ctx.create_incident(ctx.employee("karan.malhotra"), title="Payment transaction failing",
                                description="Every transaction fails on the checkout page.")
    assert {x["number"] for x in third["duplicates"]} == {first["incident"]["number"], second["incident"]["number"]}
    # both remain separate, open incidents
    assert ctx.client.get("/api/incidents?status=OPEN", headers=ctx.admin()).json()["total"] == 3


def test_unrelated_incidents_are_not_flagged(ctx):
    ctx.create_incident()
    other = ctx.create_incident(service_id=ctx.service_id("Printing"), impact=1, urgency=2, title="Printer jam on floor two",
                                description="The printer jams on every job.")
    assert other["duplicates"] == []
    same_service_other_issue = ctx.create_incident(title="Receipt PDF has wrong logo", description="The generated receipt shows an old logo.")
    assert same_service_other_issue["duplicates"] == []


def test_duplicate_check_endpoint_for_the_report_form_and_threshold_setting(ctx):
    ctx.create_incident()
    emp = ctx.employee("sneha.iyer")
    body = {"title": "Payment failing", "description": "", "service_id": ctx.service_id("Payment Gateway")}
    hits = ctx.client.post("/api/intelligence/check-duplicates", headers=emp, json=body).json()
    assert len(hits) == 1
    assert ctx.client.post("/api/intelligence/check-duplicates", headers=emp, json={"title": "ab"}).json() == []
    ctx.client.patch("/api/settings", headers=ctx.admin(), json={"duplicate_threshold": 1.0})
    assert ctx.client.post("/api/intelligence/check-duplicates", headers=emp, json=body).json() == []


def test_duplicate_detection_only_looks_at_the_last_seven_days(ctx):
    ctx.create_incident()
    ctx.clock.advance(days=8)
    again = ctx.create_incident(ctx.employee("sneha.iyer"), title="Payment application unavailable", description="Users cannot complete payment transactions.")
    assert again["duplicates"] == []


def test_admin_can_link_related_incident_without_merging(ctx):
    a = ctx.create_incident()["incident"]
    b = ctx.create_incident(ctx.employee("sneha.iyer"), title="Unable to make payment", description="Checkout errors out.")["incident"]
    r = ctx.client.patch(f"/api/incidents/{b['number']}", headers=ctx.admin(), json={"duplicate_of_number": a["number"]})
    assert r.status_code == 200 and r.json()["duplicate_of"]["number"] == a["number"]
    assert ctx.client.patch(f"/api/incidents/{b['number']}", headers=ctx.admin(), json={"duplicate_of_number": b["number"]}).status_code == 422
    assert ctx.client.get(f"/api/incidents/{a['number']}/duplicates", headers=ctx.admin()).json()[0]["number"] == b["number"]
    assert ctx.client.get(f"/api/incidents/{b['number']}", headers=ctx.admin()).json()["status"] == "ASSIGNED"  # not merged or closed


# --------------------------------------------------------------------------- SLA risk
def test_t26_high_priority_incident_close_to_deadline_is_high_risk_with_explanation(ctx):
    inc = ctx.create_incident()["incident"]
    low = ctx.client.get(f"/api/incidents/{inc['number']}", headers=ctx.admin()).json()["risk"]
    assert low["level"] == "LOW"
    ctx.clock.advance(minutes=4)  # 80% of the 5 minute response window
    high = ctx.client.get(f"/api/incidents/{inc['number']}", headers=ctx.admin()).json()["risk"]
    assert high["level"] == "HIGH" and high["points"] >= 75
    assert any("80%" in r for r in high["reasons"]) and any("P1" in r for r in high["reasons"])


def test_risk_levels_medium_unassigned_and_breached(ctx):
    admin = ctx.admin()
    unassigned = ctx.create_incident(service_id=ctx.service_id("Cloud Storage"), impact=2, urgency=2, category_id=ctx.category_id("Storage"),
                                     title="Disk quota is full on share", description="The shared drive quota is exhausted.")["incident"]
    ctx.clock.advance(minutes=20)  # P3: 20 of 60 response minutes = 33%, plus 20 for no technician = 53
    r = ctx.client.get(f"/api/incidents/{unassigned['number']}", headers=admin).json()["risk"]
    assert r["level"] == "MEDIUM" and 50 <= r["points"] < 75 and any("No technician" in x for x in r["reasons"])
    ctx.clock.advance(minutes=15)  # 58% + 20 = 78 -> HIGH
    assert ctx.client.get(f"/api/incidents/{unassigned['number']}", headers=admin).json()["risk"]["level"] == "HIGH"
    p1 = ctx.create_incident()["incident"]
    ctx.clock.advance(minutes=30)
    ctx.client.post("/api/sla/run-check", headers=admin)
    risk = ctx.client.get(f"/api/incidents/{p1['number']}", headers=admin).json()["risk"]
    assert risk["level"] == "HIGH" and "already been breached" in risk["reasons"][0]


def test_resolved_incident_has_no_risk(ctx):
    inc = ctx.create_incident()["incident"]
    tech = _tech(ctx, inc)
    ctx.transition(inc["number"], tech, "ACKNOWLEDGED")
    ctx.transition(inc["number"], tech, "IN_PROGRESS")
    ctx.transition(inc["number"], tech, "RESOLVED", resolution_summary="Fixed", root_cause="Cause")
    assert ctx.client.get(f"/api/incidents/{inc['number']}", headers=ctx.admin()).json()["risk"]["level"] == "LOW"


def test_list_items_contain_risk_level_for_open_incidents(ctx):
    ctx.create_incident()
    ctx.clock.advance(minutes=4)
    items = ctx.client.get("/api/incidents", headers=ctx.admin()).json()["items"]
    assert items[0]["risk_level"] == "HIGH"


# --------------------------------------------------------------------------- correlation and suggested resolution
def test_correlation_of_incidents_on_the_same_service(ctx):
    a = ctx.create_incident()["incident"]
    assert ctx.client.get(f"/api/incidents/{a['number']}/related", headers=ctx.admin()).json()["summary"] is None
    ctx.create_incident(ctx.employee("sneha.iyer"), title="Checkout page shows an error", description="Error when paying.")
    r = ctx.client.get(f"/api/incidents/{a['number']}/related", headers=ctx.admin()).json()
    assert len(r["related"]) == 1 and "may share a cause" in r["summary"]
    ctx.create_incident(ctx.employee("karan.malhotra"), title="Invoice payments time out", description="Timeouts when paying invoices.")
    r = ctx.client.get(f"/api/incidents/{a['number']}/related", headers=ctx.admin()).json()
    assert len(r["related"]) == 2 and "single underlying outage" in r["summary"]
    ctx.create_incident(service_id=ctx.service_id("Printing"), impact=1, urgency=1, title="Printer paper tray empty", description="Tray is always empty.")
    assert len(ctx.client.get(f"/api/incidents/{a['number']}/related", headers=ctx.admin()).json()["related"]) == 2


def test_suggested_resolution_from_similar_resolved_incidents(ctx):
    old = ctx.create_incident(title="Payment gateway returns error 500", description="Checkout shows error 500 for card payments.")["incident"]
    tech = _tech(ctx, old)
    ctx.transition(old["number"], tech, "ACKNOWLEDGED")
    ctx.transition(old["number"], tech, "IN_PROGRESS")
    ctx.transition(old["number"], tech, "RESOLVED", resolution_summary="Restarted the payment worker pool", root_cause="Exhausted worker threads")
    new = ctx.create_incident(ctx.employee("sneha.iyer"), title="Payment gateway error 500 on checkout", description="Card payments fail with error 500.")["incident"]
    tech2 = _tech(ctx, new)
    sug = ctx.client.get(f"/api/incidents/{new['number']}/suggested-resolutions", headers=tech2).json()
    assert sug and sug[0]["incident_number"] == old["number"] and "worker pool" in sug[0]["summary"]
    assert ctx.client.get(f"/api/incidents/{new['number']}/suggested-resolutions", headers=ctx.employee("sneha.iyer")).status_code == 403
