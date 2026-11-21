"""Gap-filling tests for the documented test cases TC-09, TC-11 and TC-19 (report Chapter 6).

Everything else in the documented catalogue maps to tests that already existed; these three cases had
no automated test, so they were added without touching application code.
"""
from tests.test_lifecycle import _assigned


def _payload(ctx, **patch):
    base = {"title": "Valid title here", "description": "A valid description text.",
            "service_id": ctx.service_id("Printing"), "impact": 3, "urgency": 3}
    base.update(patch)
    return base


def test_tc09_maximum_permitted_text_lengths_are_accepted_and_one_more_is_rejected(ctx):
    h = ctx.employee()
    ok = ctx.client.post("/api/incidents", headers=h,
                         json=_payload(ctx, title="T" * 200, description="D" * 5000, affected_system="S" * 200))
    assert ok.status_code == 201, ok.text
    assert len(ok.json()["incident"]["title"]) == 200
    for patch, field in [({"title": "T" * 201}, "title"), ({"description": "D" * 5001}, "description"),
                         ({"affected_system": "S" * 201}, "affected_system")]:
        r = ctx.client.post("/api/incidents", headers=h, json=_payload(ctx, **patch))
        assert r.status_code == 422, patch
        assert any(e["field"] == field for e in r.json()["errors"])


def test_tc11_missing_mandatory_fields_are_rejected_and_named(ctx):
    h = ctx.employee()
    for missing in ("title", "description", "service_id", "impact", "urgency"):
        body = _payload(ctx)
        del body[missing]
        r = ctx.client.post("/api/incidents", headers=h, json=body)
        assert r.status_code == 422, missing
        assert any(e["field"] == missing for e in r.json()["errors"]), r.json()
    assert ctx.client.post("/api/incidents", headers=h, json={}).status_code == 422


def test_tc19_technician_cannot_view_or_change_an_incident_not_assigned_to_them(ctx):
    number, assigned = _assigned(ctx)
    other = ctx.tech("vikram.singh") if assigned != ctx.tech("vikram.singh") else ctx.tech("arjun.kapoor")
    assert other != assigned
    assert ctx.client.get(f"/api/incidents/{number}", headers=other).status_code == 403
    assert ctx.client.patch(f"/api/incidents/{number}", headers=other, json={"category_id": ctx.category_id("Network")}).status_code == 403
    assert ctx.transition(number, other, "ACKNOWLEDGED").status_code == 403
    assert ctx.client.get(f"/api/incidents/{number}", headers=ctx.admin()).json()["status"] == "ASSIGNED"
