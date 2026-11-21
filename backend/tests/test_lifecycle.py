"""T08 T09 T10 T11 and the State pattern."""
import itertools

import pytest

from app.domain.enums import ActorKind, IncidentStatus
from app.domain.exceptions import InvalidInputError, InvalidTransitionError, PermissionDeniedError
from app.domain.lifecycle import LifecycleManager, StateFactory

S = IncidentStatus
ALLOWED = {
    (S.NEW, S.CLASSIFIED), (S.CLASSIFIED, S.ASSIGNED), (S.ASSIGNED, S.ACKNOWLEDGED), (S.ACKNOWLEDGED, S.IN_PROGRESS),
    (S.IN_PROGRESS, S.RESOLVED), (S.RESOLVED, S.VERIFIED), (S.RESOLVED, S.IN_PROGRESS), (S.VERIFIED, S.CLOSED),
    (S.ACKNOWLEDGED, S.ASSIGNED), (S.IN_PROGRESS, S.ASSIGNED), (S.ASSIGNED, S.ASSIGNED),
}
EVERYONE = {ActorKind.SYSTEM, ActorKind.ADMIN, ActorKind.ASSIGNED_TECH, ActorKind.REPORTER}
FULL_PAYLOAD = {"reason": "because", "resolution_summary": "fixed", "root_cause": "bug"}


@pytest.mark.parametrize("src,dst", [p for p in itertools.product(S, S) if p not in ALLOWED])
def test_every_disallowed_transition_is_rejected(src, dst):
    with pytest.raises(InvalidTransitionError):
        LifecycleManager.validate(src, dst, EVERYONE, FULL_PAYLOAD)


@pytest.mark.parametrize("src,dst", sorted(ALLOWED, key=str))
def test_every_allowed_transition_is_accepted_for_an_authorised_actor(src, dst):
    rule = LifecycleManager.validate(src, dst, EVERYONE, FULL_PAYLOAD)
    assert rule.target == dst


def test_state_objects_describe_next_states():
    assert StateFactory.for_status(S.CLOSED).next_statuses() == []
    assert S.CLASSIFIED in StateFactory.for_status(S.NEW).next_statuses()


def test_actor_rules():
    with pytest.raises(PermissionDeniedError):
        LifecycleManager.validate(S.ASSIGNED, S.ACKNOWLEDGED, {ActorKind.REPORTER})
    with pytest.raises(PermissionDeniedError):
        LifecycleManager.validate(S.RESOLVED, S.VERIFIED, {ActorKind.ASSIGNED_TECH})
    with pytest.raises(InvalidInputError):
        LifecycleManager.validate(S.IN_PROGRESS, S.RESOLVED, {ActorKind.ASSIGNED_TECH}, {"resolution_summary": "x"})


def _assigned(ctx):
    data = ctx.create_incident()["incident"]
    tech = ctx.tech(data["assigned_technician"]["full_name"].lower().replace(" ", "."))
    return data["number"], tech


def test_t08_new_to_closed_is_rejected_with_409_and_no_mutation(ctx):
    number, _ = _assigned(ctx)
    c, s = ctx.container()
    inc = c.repos.incidents.get_by_number(number)
    inc.status = S.NEW
    s.commit()
    s.close()
    r = ctx.transition(number, ctx.admin(), "CLOSED")
    assert r.status_code == 409 and r.json()["code"] == "INVALID_STATE_TRANSITION"
    c, s = ctx.container()
    assert c.repos.incidents.get_by_number(number).status == S.NEW and c.repos.incidents.get_by_number(number).closed_at is None
    s.close()


def test_assigned_to_resolved_and_assigned_to_closed_are_rejected(ctx):
    number, tech = _assigned(ctx)
    assert ctx.transition(number, tech, "RESOLVED", resolution_summary="x", root_cause="y").status_code == 409
    assert ctx.transition(number, ctx.admin(), "CLOSED").status_code == 409
    assert ctx.transition(number, ctx.admin(), "VERIFIED").status_code == 409
    assert ctx.client.get(f"/api/incidents/{number}", headers=ctx.admin()).json()["status"] == "ASSIGNED"


def test_t09_assigned_technician_acknowledges_and_timestamp_is_set(ctx):
    number, tech = _assigned(ctx)
    ctx.clock.advance(minutes=2)
    r = ctx.transition(number, tech, "ACKNOWLEDGED")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ACKNOWLEDGED" and body["acknowledged_at"].startswith("2026-01-15T09:02")
    assert body["sla"]["response"]["state"] == "MET"


def test_only_assigned_technician_or_admin_can_acknowledge(ctx):
    number, tech = _assigned(ctx)
    assert ctx.transition(number, ctx.employee(), "ACKNOWLEDGED").status_code == 403
    other = ctx.tech("vikram.singh" if tech != ctx.tech("vikram.singh") else "arjun.kapoor")
    assert ctx.transition(number, other, "ACKNOWLEDGED").status_code == 403
    assert ctx.transition(number, ctx.admin(), "ACKNOWLEDGED").status_code == 200


def test_t10_resolve_without_summary_or_root_cause_is_rejected(ctx):
    number, tech = _assigned(ctx)
    ctx.transition(number, tech, "ACKNOWLEDGED")
    ctx.transition(number, tech, "IN_PROGRESS")
    r = ctx.transition(number, tech, "RESOLVED")
    assert r.status_code == 422
    r = ctx.transition(number, tech, "RESOLVED", resolution_summary="Restarted service")
    assert r.status_code == 422 and "root cause" in r.json()["detail"]
    r = ctx.transition(number, tech, "RESOLVED", resolution_summary="   ", root_cause="Memory leak")
    assert r.status_code == 422
    assert ctx.client.get(f"/api/incidents/{number}", headers=tech).json()["status"] == "IN_PROGRESS"


def _resolved(ctx):
    number, tech = _assigned(ctx)
    ctx.transition(number, tech, "ACKNOWLEDGED")
    ctx.transition(number, tech, "IN_PROGRESS")
    r = ctx.transition(number, tech, "RESOLVED", resolution_summary="Restarted gateway", root_cause="Memory leak")
    assert r.status_code == 200
    return number, tech


def test_full_lifecycle_to_closed(ctx):
    number, tech = _resolved(ctx)
    emp = ctx.employee()
    inc = ctx.client.get(f"/api/incidents/{number}", headers=emp).json()
    assert inc["resolution"]["summary"] == "Restarted gateway" and inc["resolved_at"]
    assert inc["allowed_transitions"] == ["IN_PROGRESS", "VERIFIED"] or set(inc["allowed_transitions"]) == {"VERIFIED", "IN_PROGRESS"}
    assert ctx.transition(number, emp, "CLOSED").status_code == 409  # must be verified first
    assert ctx.transition(number, tech, "VERIFIED").status_code == 403  # technician cannot verify
    assert ctx.transition(number, emp, "VERIFIED").status_code == 200
    r = ctx.transition(number, emp, "CLOSED", closure_note="All good")
    assert r.status_code == 200 and r.json()["status"] == "CLOSED" and r.json()["closure_note"] == "All good"
    assert ctx.transition(number, emp, "IN_PROGRESS", reason="again").status_code == 409  # closed is final


def test_t11_reopen_requires_reason_and_reason_is_audited(ctx):
    number, tech = _resolved(ctx)
    emp = ctx.employee()
    assert ctx.transition(number, emp, "IN_PROGRESS").status_code == 422
    r = ctx.transition(number, emp, "IN_PROGRESS", reason="The error is still happening")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "IN_PROGRESS" and body["reopen_count"] == 1 and body["resolved_at"] is None
    tl = ctx.client.get(f"/api/incidents/{number}/timeline", headers=ctx.admin()).json()
    reopened = [e for e in tl if e["action"] == "INCIDENT_REOPENED"][0]
    assert "still happening" in reopened["description"]
    assert (reopened["previous_state"], reopened["new_state"]) == ("RESOLVED", "IN_PROGRESS")
    notes = ctx.client.get(f"/api/incidents/{number}/notes", headers=emp).json()
    assert any(n["note_type"] == "REOPEN" for n in notes)
    # the technician can resolve again, the resolution record is replaced (still one row)
    r = ctx.transition(number, tech, "RESOLVED", resolution_summary="Patched properly", root_cause="Config drift")
    assert r.status_code == 200 and r.json()["resolution"]["summary"] == "Patched properly"


def test_every_accepted_transition_is_audited_with_states(ctx):
    number, tech = _resolved(ctx)
    tl = ctx.client.get(f"/api/incidents/{number}/timeline", headers=ctx.admin()).json()
    steps = [(e["previous_state"], e["new_state"]) for e in tl if e["previous_state"] and e["new_state"]]
    for pair in [("NEW", "CLASSIFIED"), ("CLASSIFIED", "ASSIGNED"), ("ASSIGNED", "ACKNOWLEDGED"),
                 ("ACKNOWLEDGED", "IN_PROGRESS"), ("IN_PROGRESS", "RESOLVED")]:
        assert pair in steps, pair
    times = [e["created_at"] for e in tl]
    assert times == sorted(times)


def test_invalid_status_value_is_422(ctx):
    number, _ = _assigned(ctx)
    r = ctx.client.post(f"/api/incidents/{number}/transition", headers=ctx.admin(), json={"to_status": "FLYING"})
    assert r.status_code == 422


def test_admin_reassignment_from_in_progress(ctx):
    number, tech = _assigned(ctx)
    ctx.transition(number, tech, "ACKNOWLEDGED")
    ctx.transition(number, tech, "IN_PROGRESS")
    current = ctx.client.get(f"/api/incidents/{number}", headers=ctx.admin()).json()["assigned_technician"]["id"]
    new_id = ctx.user_id("pooja.desai") if current != ctx.user_id("pooja.desai") else ctx.user_id("meera.joshi")
    r = ctx.client.post(f"/api/incidents/{number}/assign", headers=ctx.admin(), json={"technician_id": new_id})
    assert r.status_code == 200 and r.json()["status"] == "ASSIGNED" and r.json()["assigned_technician"]["id"] == new_id
    tl = ctx.client.get(f"/api/incidents/{number}/timeline", headers=ctx.admin()).json()
    assert any(e["action"] == "INCIDENT_REASSIGNED" for e in tl)
    # the old technician has lost access
    assert ctx.client.get(f"/api/incidents/{number}", headers=tech).status_code == 403
