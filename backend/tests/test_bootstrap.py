"""Production start: no demo data, first administrator comes from settings."""
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.database import init_db, make_engine, make_session_factory
from app.main import create_app
from app.utils.seed import bootstrap_if_empty


def _settings(**kw):
    base = dict(database_url="sqlite://", secret_key="x" * 40, seed_demo_data=False, sla_monitor_enabled=False, bcrypt_rounds=4)
    base.update(kw)
    return Settings(**base)


def _factory():
    engine = make_engine("sqlite://")
    init_db(engine)
    return make_session_factory(engine)


def test_bootstrap_creates_admin_and_standard_configuration():
    f = _factory()
    s = _settings(initial_admin_email="boss@corp.example", initial_admin_password="Strong-pass-1")
    assert bootstrap_if_empty(f, s) is True
    assert bootstrap_if_empty(f, s) is False  # second start changes nothing
    app = create_app(s, f, start_monitor=False, seed=False)
    with TestClient(app) as c:
        r = c.post("/api/auth/login", json={"email": "boss@corp.example", "password": "Strong-pass-1"})
        assert r.status_code == 200 and r.json()["user"]["role"] == "ADMIN"
        h = {"Authorization": f"Bearer {r.json()['access_token']}"}
        assert len(c.get("/api/sla-policies", headers=h).json()) == 4
        assert len(c.get("/api/categories", headers=h).json()) == 9
        assert len(c.get("/api/services", headers=h).json()) == 8
        assert c.get("/api/incidents", headers=h).json()["total"] == 0
        assert len(c.get("/api/users", headers=h).json()) == 1  # no demo people


def test_bootstrap_without_credentials_does_nothing_and_warns(caplog):
    f = _factory()
    assert bootstrap_if_empty(f, _settings()) is False
    assert "INITIAL_ADMIN_EMAIL" in caplog.text


def test_production_refuses_the_default_secret_key():
    with pytest.raises(RuntimeError):
        create_app(_settings(app_env="production", secret_key="CHANGE_THIS_TO_A_LONG_RANDOM_SECRET"), _factory(), start_monitor=False, seed=False)
