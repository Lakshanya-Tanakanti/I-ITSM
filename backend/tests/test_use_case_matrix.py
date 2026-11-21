"""Checks the actor permissions drawn in the use case diagram against the live API."""
import pytest

from tests.use_case_matrix import USE_CASES

PROBED = [u for u in USE_CASES if u["probe"]]
ROLE_OF = {"EMPLOYEE": "employee", "TECHNICIAN": "tech", "ADMIN": "admin"}


def _body(ctx, spec, number):
    if spec == "NEW_INCIDENT":
        return {"title": "Matrix probe incident", "description": "Probe for the use case matrix.",
                "service_id": ctx.service_id("Payment Gateway"), "impact": 3, "urgency": 3}
    if spec == "PREVIEW":
        return {"service_id": ctx.service_id("Payment Gateway"), "impact": 3, "urgency": 3, "affected_users": 10}
    if spec == "DUPES":
        return {"title": "Matrix probe incident", "description": "Probe"}
    return spec


@pytest.mark.parametrize("case", PROBED, ids=lambda u: u["id"])
def test_only_listed_actors_are_allowed(ctx, case):
    method, path, spec = case["probe"]
    for role, getter in ROLE_OF.items():
        number = ctx.create_incident(headers=ctx.employee())["incident"]["number"]
        headers = getattr(ctx, getter)()
        url = path.replace("{n}", number)
        resp = ctx.client.request(method, url, headers=headers, json=_body(ctx, spec, number)
                                  if method != "GET" else None)
        allowed = role in case["actors"]
        if allowed:
            assert resp.status_code not in (401, 403), f"{case['id']} {role} should be allowed: {resp.status_code} {resp.text}"
        else:
            assert resp.status_code == 403, f"{case['id']} {role} should be denied: {resp.status_code} {resp.text}"


def test_anonymous_cannot_use_any_probed_endpoint(ctx):
    for case in PROBED:
        method, path, _ = case["probe"]
        resp = ctx.client.request(method, path.replace("{n}", "INC-000001"), json={} if method != "GET" else None)
        assert resp.status_code == 401, case["id"]


def test_diagram_ids_are_unique_and_links_resolve():
    ids = [u["id"] for u in USE_CASES]
    assert len(ids) == len(set(ids))
    for u in USE_CASES:
        for target in u["includes"] + u["extends"]:
            assert target in ids
