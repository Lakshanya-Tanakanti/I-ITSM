"""T12 T13 T14 T15 T30: eligibility, strategies, recommendations and assignment errors."""
import pytest

from app.domain.enums import Priority
from app.strategies.assignment import (
    AssignmentContext, EligibilityPolicy, LoadBasedStrategy, SkillBasedStrategy, SkillThenLoadStrategy,
    TechnicianCandidate,
)
from app.strategies.factory import StrategyFactory


def cand(uid, name, skills, load=0, limit=5, exp=3, available=True, active=True, svc=0):
    return TechnicianCandidate(uid, name, active, available, limit, load, exp, skills, service_experience=svc)


CTX = AssignmentContext(category_id=1, category_name="Network", priority=Priority.P3)


def test_t12_technician_without_skill_is_not_eligible():
    problems = EligibilityPolicy().check(cand(1, "A", {2: 5}), CTX)
    assert [p.code for p in problems] == ["NO_SKILL"]
    assert "Network" in problems[0].message


def test_t13_unavailable_inactive_or_full_technicians_are_not_eligible():
    pol = EligibilityPolicy()
    assert [p.code for p in pol.check(cand(1, "A", {1: 3}, available=False), CTX)] == ["UNAVAILABLE"]
    assert [p.code for p in pol.check(cand(1, "A", {1: 3}, active=False), CTX)] == ["INACTIVE"]
    assert [p.code for p in pol.check(cand(1, "A", {1: 3}, load=5, limit=5), CTX)] == ["AT_LIMIT"]
    assert pol.check(cand(1, "A", {1: 3}, load=4, limit=5), CTX) == []


def test_t14_skill_based_ranks_by_proficiency_then_experience():
    ranked = SkillBasedStrategy().rank([cand(1, "Low", {1: 2}, exp=10), cand(2, "High", {1: 5}, exp=1, load=4)], CTX)
    assert [r.name for r in ranked] == ["High", "Low"]
    assert [r.rank for r in ranked] == [1, 2]
    assert ranked[0].reasons and any("proficiency 5/5" in r for r in ranked[0].reasons)


def test_t14_load_based_ranks_by_free_capacity():
    ranked = LoadBasedStrategy().rank([cand(1, "Busy", {1: 5}, load=4), cand(2, "Free", {1: 1}, load=0)], CTX)
    assert [r.name for r in ranked] == ["Free", "Busy"]
    assert any("Free capacity" in r for r in ranked[0].reasons)


def test_balanced_strategy_blends_both_and_weights_skill_for_critical():
    a, b = cand(1, "Expert", {1: 5}, load=3, exp=8), cand(2, "Newbie", {1: 2}, load=0, exp=1)
    ranked = SkillThenLoadStrategy().rank([a, b], AssignmentContext(1, "Network", Priority.P1))
    assert ranked[0].name == "Expert" and any("Critical priority" in r for r in ranked[0].reasons)


def test_strategies_are_interchangeable_through_the_factory():
    names = {o["name"] for o in StrategyFactory.assignment_options()}
    assert {"skill_based", "load_based", "skill_then_load"} <= names
    people = [cand(1, "A", {1: 4}, load=2), cand(2, "B", {1: 3}, load=0)]
    for n in names:
        ranked = StrategyFactory.assignment(n).rank(people, CTX)
        assert len(ranked) == 2 and ranked[0].rank == 1 and ranked[0].reasons


def test_ranking_is_deterministic_on_ties():
    ranked = SkillBasedStrategy().rank([cand(2, "Same", {1: 3}), cand(1, "Same", {1: 3})], CTX)
    assert [r.technician_id for r in ranked] == [1, 2]


# ----------------------------------------------------------------------------- API level
def _incident_for(ctx, category="Network"):
    return ctx.create_incident(
        service_id=ctx.service_id("Campus Wi-Fi"), impact=3, urgency=3, category_id=ctx.category_id(category),
        title="Wireless problem in building", description="Nobody can connect to the wireless in the building.")["incident"]


def test_automatic_assignment_picks_a_skilled_available_technician(ctx):
    inc = _incident_for(ctx)
    assert inc["status"] == "ASSIGNED"
    assert inc["assigned_technician"]["full_name"] in ("Arjun Kapoor", "Vikram Singh")  # the Network skills


def test_t14_recommendations_endpoint_for_each_strategy(ctx):
    inc = _incident_for(ctx, "Cloud")  # Arjun (3) assigned automatically, Imran is unavailable
    admin = ctx.admin()
    for strategy in ("skill_based", "load_based", "skill_then_load"):
        r = ctx.client.get(f"/api/incidents/{inc['number']}/recommendations?strategy={strategy}", headers=admin)
        assert r.status_code == 200
        body = r.json()
        assert body["strategy"]["name"] == strategy
        names_ineligible = {i["name"] for i in body["ineligible"]}
        assert "Imran Khan" in names_ineligible
        imran = [i for i in body["ineligible"] if i["name"] == "Imran Khan"][0]
        assert "Marked unavailable" in imran["reasons"]
        for rec in body["eligible"]:
            assert rec["reasons"] and rec["rank"] >= 1
    assert ctx.client.get(f"/api/incidents/{inc['number']}/recommendations?strategy=bogus", headers=admin).status_code == 422


def test_t15_no_eligible_technician_leaves_incident_unassigned_and_notifies_admin(ctx):
    # Storage is only covered by Imran, who is on leave.
    data = ctx.create_incident(service_id=ctx.service_id("Cloud Storage"), impact=2, urgency=2,
                               category_id=ctx.category_id("Storage"), title="Disk quota is full on share",
                               description="The shared drive quota is exhausted for everybody.")
    inc = data["incident"]
    assert data["assigned"] is False and inc["status"] == "CLASSIFIED" and inc["assigned_technician"] is None
    assert "No eligible technician" in data["assignment_message"]
    notes = ctx.client.get("/api/notifications", headers=ctx.admin()).json()["items"]
    assert any("No eligible technician" in n["subject"] for n in notes)
    tl = ctx.client.get(f"/api/incidents/{inc['number']}/timeline", headers=ctx.admin()).json()
    entry = [e for e in tl if e["action"] == "NO_TECHNICIAN_AVAILABLE"][0]
    assert "Imran Khan" in entry["description"] and "unavailable" in entry["description"].lower()
    # employees do not see the internal routing detail
    emp_tl = ctx.client.get(f"/api/incidents/{inc['number']}/timeline", headers=ctx.employee()).json()
    assert not any(e["action"] == "NO_TECHNICIAN_AVAILABLE" for e in emp_tl)


def test_admin_assigns_manually_after_making_technician_available(ctx):
    data = ctx.create_incident(service_id=ctx.service_id("Cloud Storage"), impact=2, urgency=2,
                               category_id=ctx.category_id("Storage"), title="Disk quota is full on share",
                               description="The shared drive quota is exhausted for everybody.")
    number = data["incident"]["number"]
    imran = ctx.user_id("imran.khan")
    admin = ctx.admin()
    r = ctx.client.post(f"/api/incidents/{number}/assign", headers=admin, json={"technician_id": imran})
    assert r.status_code == 409 and r.json()["code"] == "TECHNICIAN_UNAVAILABLE"
    ctx.client.put(f"/api/users/{imran}/technician-profile", headers=admin, json={"is_available": True})
    r = ctx.client.post(f"/api/incidents/{number}/assign", headers=admin, json={"technician_id": imran})
    assert r.status_code == 200 and r.json()["assigned_technician"]["full_name"] == "Imran Khan"
    assert r.json()["status"] == "ASSIGNED"
    # assigning the same technician again conflicts
    assert ctx.client.post(f"/api/incidents/{number}/assign", headers=admin, json={"technician_id": imran}).status_code == 409


def test_workload_limit_blocks_assignment_unless_admin_overrides(ctx):
    admin = ctx.admin()
    meera = ctx.user_id("meera.joshi")
    pooja = ctx.user_id("pooja.desai")
    ctx.client.put(f"/api/users/{meera}/technician-profile", headers=admin, json={"workload_limit": 1})
    ctx.client.put(f"/api/users/{pooja}/technician-profile", headers=admin, json={"is_available": False})
    first = ctx.create_incident()["incident"]
    assert first["assigned_technician"]["id"] == meera  # now at 1/1
    # second Application incident: Meera is full, Pooja unavailable -> unassigned
    second = ctx.create_incident(title="Another payment failure", description="Payments fail again for several customers.")
    assert second["assigned"] is False
    n = second["incident"]["number"]
    r = ctx.client.post(f"/api/incidents/{n}/assign", headers=admin, json={"technician_id": meera})
    assert r.status_code == 409 and r.json()["code"] == "TECHNICIAN_WORKLOAD_EXCEEDED"
    r = ctx.client.post(f"/api/incidents/{n}/assign", headers=admin, json={"technician_id": meera, "override": True})
    assert r.status_code == 200
    tl = ctx.client.get(f"/api/incidents/{n}/timeline", headers=admin).json()
    assigned = [e for e in tl if e["action"] == "INCIDENT_ASSIGNED"][0]
    assert "override" in assigned["description"].lower()


def test_missing_skill_needs_explicit_override_and_is_audited(ctx):
    inc = _incident_for(ctx, "Network")
    admin = ctx.admin()
    pooja = ctx.user_id("pooja.desai")  # no Network skill
    r = ctx.client.post(f"/api/incidents/{inc['number']}/assign", headers=admin, json={"technician_id": pooja})
    assert r.status_code == 409 and r.json()["code"] == "TECHNICIAN_MISSING_SKILL"
    r = ctx.client.post(f"/api/incidents/{inc['number']}/assign", headers=admin, json={"technician_id": pooja, "override": True})
    assert r.status_code == 200
    log = ctx.client.get("/api/audit-logs?action=INCIDENT_REASSIGNED", headers=admin).json()["items"]
    assert any("Lacks the Network skill" in e["description"] for e in log)


def test_cannot_assign_a_non_technician_or_unknown_user(ctx):
    inc = _incident_for(ctx)
    admin = ctx.admin()
    r = ctx.client.post(f"/api/incidents/{inc['number']}/assign", headers=admin, json={"technician_id": ctx.user_id("rahul.verma")})
    assert r.status_code == 404
    assert ctx.client.post(f"/api/incidents/{inc['number']}/assign", headers=admin, json={"technician_id": 9999}).status_code == 404


def test_t30_admin_changes_strategy_and_recommendations_follow(ctx):
    inc = _incident_for(ctx)
    admin = ctx.admin()
    r = ctx.client.patch("/api/settings", headers=admin, json={"assignment_strategy": "load_based"})
    assert r.status_code == 200 and r.json()["settings"]["assignment_strategy"] == "load_based"
    rec = ctx.client.get(f"/api/incidents/{inc['number']}/recommendations", headers=admin).json()
    assert rec["strategy"]["name"] == "load_based"
    assert ctx.client.patch("/api/settings", headers=admin, json={"assignment_strategy": "nope"}).status_code == 422
    assert ctx.client.patch("/api/settings", headers=admin, json={"duplicate_threshold": 5}).status_code == 422
    log = ctx.client.get("/api/audit-logs?action=CONFIG_CHANGED", headers=admin).json()["items"]
    assert any("assignment_strategy" in e["description"] for e in log)


def test_auto_assign_can_be_switched_off(ctx):
    ctx.client.patch("/api/settings", headers=ctx.admin(), json={"auto_assign": False})
    data = ctx.create_incident()
    assert data["assigned"] is False and data["incident"]["status"] == "CLASSIFIED"
    assert "switched off" in data["assignment_message"]


def test_cannot_deactivate_technician_with_active_incidents(ctx):
    inc = ctx.create_incident()["incident"]
    tid = inc["assigned_technician"]["id"]
    r = ctx.client.post(f"/api/users/{tid}/deactivate", headers=ctx.admin())
    assert r.status_code == 409
    assert "active incidents" in r.json()["detail"]
