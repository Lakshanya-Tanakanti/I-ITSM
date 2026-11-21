"""T05 T06 T07: priority calculation (Strategy pattern) and business rule BR-01..BR-03."""
import pytest

from app.domain.enums import Priority
from app.domain.exceptions import InvalidInputError
from app.strategies.factory import StrategyFactory
from app.strategies.priority import ScoreProductPriorityStrategy, WeightedPriorityStrategy

strategy = ScoreProductPriorityStrategy()


def test_t05_impact4_urgency5_criticality5_is_score_100_p1():
    r = strategy.calculate(4, 5, 5)
    assert r.score == 100 and r.priority == Priority.P1


@pytest.mark.parametrize("score,expected", [
    (1, Priority.P4), (7, Priority.P4), (8, Priority.P3), (19, Priority.P3), (20, Priority.P2),
    (39, Priority.P2), (40, Priority.P1), (125, Priority.P1),
])
def test_t06_t07_threshold_boundaries(score, expected):
    assert ScoreProductPriorityStrategy.level_for_score(score) == expected


@pytest.mark.parametrize("ratings,score,expected", [
    ((1, 2, 1), 2, Priority.P4),        # one printer jammed
    ((3, 3, 2), 18, Priority.P3),       # library catalogue
    ((3, 3, 4), 36, Priority.P2),       # student portal slow
    ((4, 5, 5), 100, Priority.P1),      # payment app down
    ((2, 4, 1), 8, Priority.P3),        # exactly 8
    ((1, 4, 5), 20, Priority.P2),       # exactly 20
    ((2, 4, 5), 40, Priority.P1),       # exactly 40
    ((1, 1, 1), 1, Priority.P4), ((5, 5, 5), 125, Priority.P1),
])
def test_documented_examples_and_boundaries(ratings, score, expected):
    r = strategy.calculate(*ratings)
    assert (r.score, r.priority) == (score, expected)
    assert "=" in r.explanation


@pytest.mark.parametrize("bad", [(0, 3, 3), (6, 3, 3), (3, 0, 3), (3, 3, 6), (-1, 1, 1)])
def test_invalid_ratings_are_rejected(bad):
    with pytest.raises(InvalidInputError):
        strategy.calculate(*bad)


def test_score_outside_range_is_rejected():
    for bad in (0, 126, -5):
        with pytest.raises(InvalidInputError):
            ScoreProductPriorityStrategy.level_for_score(bad)


def test_weighted_strategy_is_interchangeable():
    w = WeightedPriorityStrategy()
    assert w.calculate(5, 5, 5).priority == Priority.P1
    assert w.calculate(1, 1, 1).priority == Priority.P4
    assert isinstance(StrategyFactory.priority("weighted"), WeightedPriorityStrategy)
    with pytest.raises(InvalidInputError):
        StrategyFactory.priority("unknown")


def test_api_calculates_priority_and_takes_criticality_from_service(ctx):
    # Library System criticality is 2: 3 x 3 x 2 = 18 -> P3
    data = ctx.create_incident(service_id=ctx.service_id("Library System"), impact=3, urgency=3,
                               title="Library catalogue search broken", description="Search returns nothing at all.")
    inc = data["incident"]
    assert inc["priority_score"] == 18 and inc["priority"] == "P3" and inc["business_criticality"] == 2
    assert inc["criticality_overridden"] is False


def test_employee_cannot_override_criticality_but_admin_can(ctx):
    sid = ctx.service_id("Printing")  # criticality 1
    emp = ctx.create_incident(service_id=sid, impact=2, urgency=2, business_criticality=5,
                              title="Printer jam on floor one", description="Printer jams on every job.")["incident"]
    assert emp["business_criticality"] == 1 and emp["priority"] == "P4"
    adm = ctx.create_incident(ctx.admin(), service_id=sid, impact=2, urgency=2, business_criticality=5,
                              title="Printer jam on floor two", description="Printer jams on every job.")["incident"]
    assert adm["business_criticality"] == 5 and adm["criticality_overridden"] is True
    assert adm["priority_score"] == 20 and adm["priority"] == "P2"


def test_incident_validation_errors_are_meaningful(ctx):
    h = ctx.employee()
    base = {"title": "Valid title here", "description": "A valid description text.",
            "service_id": ctx.service_id("Printing"), "impact": 3, "urgency": 3}
    for patch, field in [({"title": "abc"}, "title"), ({"description": "short"}, "description"),
                         ({"impact": 6}, "impact"), ({"urgency": 0}, "urgency")]:
        r = ctx.client.post("/api/incidents", headers=h, json={**base, **patch})
        assert r.status_code == 422, patch
        assert any(e["field"] == field for e in r.json()["errors"]), r.json()
    r = ctx.client.post("/api/incidents", headers=h, json={**base, "service_id": 9999})
    assert r.status_code == 404 and r.json()["code"] == "SERVICE_NOT_FOUND"
    r = ctx.client.post("/api/incidents", headers=h, json={**base, "category_id": 9999})
    assert r.status_code == 422


def test_admin_priority_change_recalculates_priority_and_sla(ctx):
    inc = ctx.create_incident()["incident"]
    assert inc["priority"] == "P1"
    r = ctx.client.patch(f"/api/incidents/{inc['number']}", headers=ctx.admin(), json={"impact": 1, "urgency": 1})
    assert r.status_code == 200
    new = r.json()
    assert new["priority_score"] == 5 and new["priority"] == "P4"
    assert new["sla"]["response"]["target_minutes"] == 240
    tl = ctx.client.get(f"/api/incidents/{inc['number']}/timeline", headers=ctx.admin()).json()
    assert any(e["action"] == "PRIORITY_CHANGED" and e["previous_state"] == "P1" and e["new_state"] == "P4" for e in tl)


def test_changing_priority_strategy_setting_changes_calculation(ctx):
    ctx.client.patch("/api/settings", headers=ctx.admin(), json={"priority_strategy": "weighted"})
    inc = ctx.create_incident(service_id=ctx.service_id("Printing"), impact=1, urgency=1,
                              title="Tiny printer issue here", description="Very small problem on printer.")["incident"]
    assert inc["priority"] == "P4"
