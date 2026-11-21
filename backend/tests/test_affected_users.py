"""Affected-user count as an input to the priority calculation (impact floor)."""
import pytest

from app.strategies.priority import AffectedUsersPolicy


# --------------------------------------------------------------------------- the policy itself
@pytest.mark.parametrize("users,floor", [
    (None, 1), (0, 1), (9, 1), (10, 2), (49, 2), (50, 3), (249, 3), (250, 4), (999, 4), (1000, 5), (1_000_000, 5),
])
def test_floor_bands_and_their_boundaries(users, floor):
    assert AffectedUsersPolicy.floor_for(users) == floor


@pytest.mark.parametrize("bad", [-1, "50", 2.5, True])
def test_invalid_user_counts_give_no_floor(bad):
    assert AffectedUsersPolicy.floor_for(bad) == 1


def test_adjust_only_raises_never_lowers():
    assert AffectedUsersPolicy.adjust(2, 1000) == (5, "Impact raised from 2 to 5 because 1000 users are affected.")
    assert AffectedUsersPolicy.adjust(5, 10) == (5, None)       # reporter said 5, few users: keep 5
    assert AffectedUsersPolicy.adjust(3, 50) == (3, None)       # floor equal to impact: no change
    assert AffectedUsersPolicy.adjust(3, None) == (3, None)


# --------------------------------------------------------------------------- through the API
def _create(ctx, users, impact=2, urgency=3, **extra):
    return ctx.create_incident(impact=impact, urgency=urgency, affected_users=users,
                               service_id=ctx.service_id("Library System"), title="Catalogue search is unavailable",
                               description="Nobody can search the catalogue at the moment.", **extra)["incident"]


def test_many_affected_users_raise_the_priority_and_the_original_rating_is_kept(ctx):
    base = _create(ctx, None)                  # Library System criticality 2 (per seed): 2 x 3 x c
    crit = base["business_criticality"]
    big = _create(ctx, 1000)
    assert big["impact"] == 2 and big["effective_impact"] == 5          # reported value preserved
    assert big["priority_score"] == 5 * 3 * crit and base["priority_score"] == 2 * 3 * crit
    assert big["priority_score"] > base["priority_score"]


def test_without_user_count_behaviour_is_exactly_the_specified_formula(ctx):
    inc = ctx.create_incident(impact=4, urgency=5)["incident"]                # T05 inputs, no affected_users
    assert inc["priority_score"] == 100 and inc["priority"] == "P1" and inc["effective_impact"] == 4


def test_the_explanation_in_the_audit_trail_mentions_the_adjustment(ctx):
    inc = _create(ctx, 300)
    tl = ctx.client.get(f"/api/incidents/{inc['number']}/timeline", headers=ctx.admin()).json()
    calc = next(e for e in tl if e["action"] == "PRIORITY_CALCULATED")
    assert "Impact raised from 2 to 4 because 300 users are affected" in calc["description"]


def test_higher_priority_gets_tighter_sla_deadlines(ctx):
    low = _create(ctx, 5, impact=1, urgency=2)
    high = _create(ctx, 5000, impact=1, urgency=2)
    assert high["priority"] != low["priority"]
    assert high["resolution_deadline"] < low["resolution_deadline"]


def test_editing_the_user_count_recalculates_priority_and_is_audited(ctx):
    inc = _create(ctx, None)
    n, emp = inc["number"], ctx.employee()
    r = ctx.client.patch(f"/api/incidents/{n}", headers=emp, json={"affected_users": 2000})
    assert r.status_code == 200 and r.json()["effective_impact"] == 5 and r.json()["priority_score"] > inc["priority_score"]
    tl = ctx.client.get(f"/api/incidents/{n}/timeline", headers=ctx.admin()).json()
    assert any(e["action"] == "PRIORITY_CHANGED" and "affected users changed to 2000" in e["description"] for e in tl)
    # lowering the count lowers the effective impact again, but never below what was reported
    r = ctx.client.patch(f"/api/incidents/{n}", headers=emp, json={"affected_users": 3})
    assert r.json()["effective_impact"] == 2 and r.json()["priority_score"] == inc["priority_score"]


def test_admin_impact_edit_uses_the_floor_too(ctx):
    inc = _create(ctx, 300)                                    # floor 4
    r = ctx.client.patch(f"/api/incidents/{inc['number']}", headers=ctx.admin(), json={"impact": 1})
    assert r.json()["impact"] == 1 and r.json()["effective_impact"] == 4
    r = ctx.client.patch(f"/api/incidents/{inc['number']}", headers=ctx.admin(), json={"impact": 5})
    assert r.json()["effective_impact"] == 5


def test_admin_can_switch_the_rule_off_and_back_on(ctx):
    admin = ctx.admin()
    assert ctx.client.get("/api/settings", headers=admin).json()["settings"]["affected_users_adjustment"] is True
    assert ctx.client.patch("/api/settings", headers=admin, json={"affected_users_adjustment": False}).status_code == 200
    off = _create(ctx, 5000)
    assert off["effective_impact"] == 2 and off["priority_score"] == 2 * 3 * off["business_criticality"]
    ctx.client.patch("/api/settings", headers=admin, json={"affected_users_adjustment": True})
    assert _create(ctx, 5000)["effective_impact"] == 5
    assert ctx.client.patch("/api/settings", headers=ctx.employee(), json={"affected_users_adjustment": False}).status_code == 403


def test_preview_endpoint_matches_what_creation_will_do(ctx):
    emp = ctx.employee()
    body = {"service_id": ctx.service_id("Library System"), "impact": 2, "urgency": 3, "affected_users": 1000}
    p = ctx.client.post("/api/intelligence/preview-priority", headers=emp, json=body).json()
    created = _create(ctx, 1000)
    assert (p["score"], p["priority"], p["effective_impact"]) == (created["priority_score"], created["priority"], 5)
    assert p["impact_raised"] is True and "raised from 2 to 5" in p["explanation"]
    # invalid input and unknown service
    assert ctx.client.post("/api/intelligence/preview-priority", headers=emp, json={**body, "impact": 9}).status_code == 422
    assert ctx.client.post("/api/intelligence/preview-priority", headers=emp, json={**body, "service_id": 999}).status_code == 404
    assert ctx.client.post("/api/intelligence/preview-priority", json=body).status_code == 401
    # only an admin can preview a criticality override
    adm = ctx.admin()
    base = ctx.client.post("/api/intelligence/preview-priority", headers=adm, json={**body, "affected_users": None}).json()
    over = ctx.client.post("/api/intelligence/preview-priority", headers=adm, json={**body, "affected_users": None, "business_criticality": 5}).json()
    ignored = ctx.client.post("/api/intelligence/preview-priority", headers=emp, json={**body, "affected_users": None, "business_criticality": 5}).json()
    assert over["business_criticality"] == 5 and ignored["business_criticality"] == base["business_criticality"]


def test_weighted_strategy_also_receives_the_effective_impact(ctx):
    ctx.client.patch("/api/settings", headers=ctx.admin(), json={"priority_strategy": "weighted"})
    low, high = _create(ctx, None), _create(ctx, 5000)
    assert high["priority_score"] > low["priority_score"]


def test_old_database_without_the_new_column_is_upgraded_automatically(tmp_path):
    import sqlite3
    from app.database import init_db, make_engine
    path = tmp_path / "old.db"
    engine = make_engine(f"sqlite:///{path}")
    init_db(engine)
    con = sqlite3.connect(path)
    con.execute("ALTER TABLE incidents DROP COLUMN effective_impact")   # simulate the previous version
    con.commit(); con.close()
    init_db(engine)                                                      # what happens on the next start
    cols = [r[1] for r in sqlite3.connect(path).execute("PRAGMA table_info(incidents)")]
    assert "effective_impact" in cols
