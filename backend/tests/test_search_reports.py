"""T23 T27 T28: filtering, sorting, pagination, dashboards and persistence."""
from datetime import timezone

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.config import Settings
from app.database import init_db, make_engine, make_session_factory
from app.domain.clock import MutableClock
from app.main import create_app
from app.services.container import build_container
from app.utils.seed import ADMIN_PASSWORD, EMPLOYEE_PASSWORD, _create_reference_data
from tests.conftest import START


def _tech(ctx, inc):
    return ctx.tech(inc["assigned_technician"]["full_name"].lower().replace(" ", "."))


def _populate(ctx):
    out = {}
    out["pay"] = ctx.create_incident()["incident"]  # P1
    out["wifi"] = ctx.create_incident(ctx.employee("sneha.iyer"), service_id=ctx.service_id("Campus Wi-Fi"), impact=3, urgency=3,
                                      title="Wi-Fi drops in the library", description="Wireless disconnects every few minutes.")["incident"]  # P2
    out["lib"] = ctx.create_incident(ctx.employee("karan.malhotra"), service_id=ctx.service_id("Library System"), impact=3, urgency=3,
                                     title="Library catalogue search broken", description="The catalogue search returns nothing.")["incident"]  # P3
    out["print"] = ctx.create_incident(ctx.employee("divya.nair"), service_id=ctx.service_id("Printing"), impact=1, urgency=2,
                                       title="Printer jam on the second floor", description="The printer jams on every job.")["incident"]  # P4
    return out


def _get(ctx, query, headers=None):
    r = ctx.client.get(f"/api/incidents?{query}", headers=headers or ctx.admin())
    assert r.status_code == 200, r.text
    return r.json()


def _numbers(res):
    return sorted(i["number"] for i in res["items"])


def test_t23_combined_filters_return_only_matching_incidents(ctx):
    inc = _populate(ctx)
    assert [inc[k]["priority"] for k in ("pay", "wifi", "lib", "print")] == ["P1", "P2", "P3", "P4"]
    ctx.clock.advance(minutes=4)
    ctx.transition(inc["pay"]["number"], _tech(ctx, inc["pay"]), "ACKNOWLEDGED")
    ctx.clock.advance(minutes=8)  # wifi has used 12 of its 15 response minutes (80%)
    ctx.client.post("/api/sla/run-check", headers=ctx.admin())

    pay_svc, wifi_svc = inc["pay"]["service"]["id"], inc["wifi"]["service"]["id"]
    assert _numbers(_get(ctx, f"status=ACKNOWLEDGED&priority=P1&service_id={pay_svc}")) == [inc["pay"]["number"]]
    assert _numbers(_get(ctx, "sla_status=AT_RISK")) == [inc["wifi"]["number"]]
    assert _numbers(_get(ctx, f"status=ASSIGNED&priority=P2&service_id={wifi_svc}&sla_status=AT_RISK")) == [inc["wifi"]["number"]]
    assert _get(ctx, f"status=ASSIGNED&priority=P2&service_id={wifi_svc}&sla_status=ON_TRACK")["total"] == 0
    assert _get(ctx, f"status=ACKNOWLEDGED&priority=P2&service_id={wifi_svc}")["total"] == 0
    assert _numbers(_get(ctx, "priority=P1,P2")) == sorted([inc["pay"]["number"], inc["wifi"]["number"]])
    assert _numbers(_get(ctx, "sla_status=ON_TRACK,AT_RISK")) == sorted(i["number"] for i in inc.values())


def test_each_of_the_eight_filters_works_on_its_own(ctx):
    inc = _populate(ctx)
    pay = inc["pay"]
    # 1 incident number
    assert _numbers(_get(ctx, "number=" + pay["number"])) == [pay["number"]]
    assert _numbers(_get(ctx, "number=1002")) == [inc["wifi"]["number"]]
    # 2 date range
    assert _get(ctx, "from_date=2026-01-15&to_date=2026-01-15")["total"] == 4
    assert _get(ctx, "from_date=2026-01-16")["total"] == 0
    assert _get(ctx, "to_date=2026-01-14")["total"] == 0
    # 3 status
    assert _get(ctx, "status=ASSIGNED")["total"] == 4 and _get(ctx, "status=CLOSED")["total"] == 0
    # 4 priority
    assert _numbers(_get(ctx, "priority=P4")) == [inc["print"]["number"]]
    # 5 category
    assert pay["number"] in _numbers(_get(ctx, f"category_id={pay['category']['id']}"))
    # 6 service
    assert _numbers(_get(ctx, f"service_id={inc['lib']['service']['id']}")) == [inc["lib"]["number"]]
    # 7 technician
    tid = pay["assigned_technician"]["id"]
    res = _get(ctx, f"technician_id={tid}")
    assert pay["number"] in _numbers(res) and all(i["assigned_technician"]["id"] == tid for i in res["items"])
    # 8 SLA status
    assert _get(ctx, "sla_status=BREACHED")["total"] == 0
    ctx.clock.advance(minutes=10)
    ctx.client.post("/api/sla/run-check", headers=ctx.admin())
    assert pay["number"] in _numbers(_get(ctx, "sla_status=BREACHED"))


def test_free_text_search_sorting_and_pagination(ctx):
    inc = _populate(ctx)
    assert _numbers(_get(ctx, "q=printer")) == [inc["print"]["number"]]
    assert _numbers(_get(ctx, "q=CATALOGUE")) == [inc["lib"]["number"]]
    assert _get(ctx, "q=zzzzqqq")["total"] == 0
    first = _get(ctx, "sort=-priority")["items"][0]
    assert first["number"] == inc["pay"]["number"]
    assert _get(ctx, "sort=priority")["items"][0]["number"] == inc["print"]["number"]
    assert [i["number"] for i in _get(ctx, "sort=number")["items"]] == sorted(i["number"] for i in inc.values())
    p1 = _get(ctx, "page=1&page_size=3&sort=number")
    p2 = _get(ctx, "page=2&page_size=3&sort=number")
    assert p1["total"] == 4 and p1["pages"] == 2 and len(p1["items"]) == 3 and len(p2["items"]) == 1
    assert not set(_numbers(p1)) & set(_numbers(p2))
    assert _get(ctx, "page=9&page_size=3")["items"] == []


def test_filter_validation_errors(ctx):
    admin = ctx.admin()
    for q in ("status=FLYING", "priority=P9", "sla_status=MAYBE", "page_size=1000", "page=0",
              "from_date=2026-02-01&to_date=2026-01-01", "from_date=not-a-date"):
        assert ctx.client.get(f"/api/incidents?{q}", headers=admin).status_code == 422, q


def test_status_aliases_and_unassigned_filter(ctx):
    inc = _populate(ctx)
    ctx.create_incident(service_id=ctx.service_id("Cloud Storage"), impact=2, urgency=2, category_id=ctx.category_id("Storage"),
                        title="Disk quota is full on share", description="The shared drive quota is exhausted for everybody.")
    assert _get(ctx, "status=OPEN")["total"] == 5
    assert _get(ctx, "status=DONE")["total"] == 0
    un = _get(ctx, "unassigned=true")
    assert un["total"] == 1 and un["items"][0]["status"] == "CLASSIFIED"
    tech = _tech(ctx, inc["pay"])
    ctx.transition(inc["pay"]["number"], tech, "ACKNOWLEDGED")
    ctx.transition(inc["pay"]["number"], tech, "IN_PROGRESS")
    ctx.transition(inc["pay"]["number"], tech, "RESOLVED", resolution_summary="Fixed", root_cause="Cause")
    assert _get(ctx, "status=DONE")["total"] == 1 and _get(ctx, "status=OPEN")["total"] == 4


def test_t27_dashboard_and_report_totals_match_database(ctx):
    inc = _populate(ctx)
    pay = inc["pay"]
    tech = _tech(ctx, pay)
    ctx.clock.advance(minutes=2)
    ctx.transition(pay["number"], tech, "ACKNOWLEDGED")
    ctx.transition(pay["number"], tech, "IN_PROGRESS")
    ctx.clock.advance(minutes=10)
    ctx.transition(pay["number"], tech, "RESOLVED", resolution_summary="Fixed", root_cause="Cause")
    ctx.transition(pay["number"], ctx.employee(), "VERIFIED")
    ctx.transition(pay["number"], ctx.employee(), "CLOSED")
    ctx.clock.advance(minutes=20)
    ctx.client.post("/api/sla/run-check", headers=ctx.admin())
    admin = ctx.admin()

    ov = ctx.client.get("/api/reports/overview", headers=admin).json()
    c, s = ctx.container()
    q = lambda sql: s.execute(text(sql)).scalar()
    assert ov["total"] == q("select count(*) from incidents") == 4
    assert ov["open"] == q("select count(*) from incidents where status in ('NEW','CLASSIFIED','ASSIGNED','ACKNOWLEDGED','IN_PROGRESS')") == 3
    assert ov["resolved"] == q("select count(*) from incidents where status in ('RESOLVED','VERIFIED','CLOSED')") == 1
    assert ov["closed"] == 1 and ov["critical"] == 0 and ov["critical_total"] == 1
    assert ov["sla_violations"] == q("select count(*) from sla_violations")
    assert ov["sla_compliance_percent"] == 100.0
    assert ov["avg_resolution_minutes"] == 12.0
    assert sum(ov["by_priority"].values()) == 4 and sum(ov["by_status"].values()) == 4
    s.close()

    by_service = ctx.client.get("/api/reports/by-service", headers=admin).json()
    by_cat = ctx.client.get("/api/reports/by-category", headers=admin).json()
    assert sum(r["total"] for r in by_service) == 4 and sum(r["total"] for r in by_cat) == 4
    assert len(by_service) == 8 and len(by_cat) == 9  # services/categories without incidents are listed with 0
    trends = ctx.client.get("/api/reports/trends?days=7", headers=admin).json()
    assert len(trends) == 7 and sum(t["created"] for t in trends) == 4 and sum(t["resolved"] for t in trends) == 1
    workload = ctx.client.get("/api/reports/technician-workload", headers=admin).json()
    assert len(workload) == 5 and sum(w["active_incidents"] for w in workload) == 3
    assert all(0 <= w["utilization_percent"] <= 100 for w in workload)

    dash = ctx.client.get("/api/dashboard", headers=admin).json()
    assert dash["role"] == "ADMIN" and dash["overview"]["total"] == 4
    assert len(dash["trends"]) == 14 and len(dash["technician_workload"]) == 5
    assert dash["recent_activity"] and dash["notifications"]["unread"] > 0


def test_sla_compliance_drops_when_a_resolved_incident_breached(ctx):
    inc = ctx.create_incident()["incident"]
    tech = _tech(ctx, inc)
    ctx.clock.advance(minutes=1)
    ctx.transition(inc["number"], tech, "ACKNOWLEDGED")
    ctx.transition(inc["number"], tech, "IN_PROGRESS")
    ctx.clock.advance(minutes=60)
    ctx.transition(inc["number"], tech, "RESOLVED", resolution_summary="Late fix", root_cause="Slow")
    ov = ctx.client.get("/api/reports/overview", headers=ctx.admin()).json()
    assert ov["sla_compliance_percent"] == 0.0 and ov["sla_violations"] == 1


def test_role_specific_dashboards(ctx):
    inc = _populate(ctx)
    emp = ctx.client.get("/api/dashboard", headers=ctx.employee("rahul.verma")).json()
    assert emp["role"] == "EMPLOYEE" and emp["counts"]["total"] == 1 and emp["counts"]["critical"] == 1
    assert emp["recent_incidents"][0]["number"] == inc["pay"]["number"] and emp["notifications"]["unread"] > 0
    tech_h = _tech(ctx, inc["pay"])
    td = ctx.client.get("/api/dashboard", headers=tech_h).json()
    assert td["role"] == "TECHNICIAN" and td["workload"]["limit"] == 5
    assert td["workload"]["active"] == td["counts"]["assigned_open"] == len(td["queue"]) >= 1
    assert td["queue"][0]["priority"] == "P1" and td["sla_countdown"][0]["remaining_seconds"] is not None
    q = ctx.client.get("/api/technicians/me/queue", headers=tech_h).json()
    assert q["total"] == td["counts"]["assigned_open"]
    # employee dashboard shows what waits for their verification
    pay = inc["pay"]
    ctx.transition(pay["number"], tech_h, "ACKNOWLEDGED")
    ctx.transition(pay["number"], tech_h, "IN_PROGRESS")
    ctx.transition(pay["number"], tech_h, "RESOLVED", resolution_summary="Fixed", root_cause="Cause")
    emp = ctx.client.get("/api/dashboard", headers=ctx.employee("rahul.verma")).json()
    assert [i["number"] for i in emp["pending_verification"]] == [pay["number"]]


def test_t28_data_persists_after_application_restart(tmp_path):
    url = f"sqlite:///{tmp_path / 'persist.db'}"
    settings = Settings(sla_monitor_enabled=False, seed_demo_data=False, database_url=url)
    clock = MutableClock(START)

    def boot():
        engine = make_engine(url)
        init_db(engine)
        factory = make_session_factory(engine)
        return engine, factory, create_app(settings=settings, session_factory=factory, clock=clock, start_monitor=False, seed=False)

    engine, factory, app = boot()
    with factory() as s:
        _create_reference_data(build_container(s, clock, settings), clock.now())
    with TestClient(app) as client:
        token = client.post("/api/auth/login", json={"email": "rahul.verma@iitsm.example.com", "password": EMPLOYEE_PASSWORD}).json()["access_token"]
        h = {"Authorization": f"Bearer {token}"}
        svc = [s for s in client.get("/api/services", headers=h).json() if s["name"] == "Payment Gateway"][0]["id"]
        r = client.post("/api/incidents", headers=h, json={"title": "Payment application unavailable",
                        "description": "Users cannot complete payment transactions.", "service_id": svc, "impact": 4, "urgency": 5})
        number = r.json()["incident"]["number"]
    engine.dispose()  # "stop" the application

    engine2, factory2, app2 = boot()  # "start" it again on the same database file
    with TestClient(app2) as client:
        token = client.post("/api/auth/login", json={"email": "rahul.verma@iitsm.example.com", "password": EMPLOYEE_PASSWORD}).json()["access_token"]
        got = client.get(f"/api/incidents/{number}", headers={"Authorization": f"Bearer {token}"})
        assert got.status_code == 200 and got.json()["title"] == "Payment application unavailable"
        admin = client.post("/api/auth/login", json={"email": "admin@iitsm.example.com", "password": ADMIN_PASSWORD}).json()["access_token"]
        assert client.get("/api/audit-logs?number=" + number, headers={"Authorization": f"Bearer {admin}"}).json()["total"] >= 4
    engine2.dispose()
