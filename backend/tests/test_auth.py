"""T01 T02 T03 and further authentication tests."""
from app.models import AuditLog, User
from app.utils.security import hash_password, verify_password


def test_t01_register_valid_employee_and_password_is_hashed(ctx):
    r = ctx.client.post("/api/auth/register", json={
        "full_name": "New Person", "email": "new.person@iitsm.example.com", "password": "Secret123", "department": "Legal"})
    assert r.status_code == 201
    body = r.json()
    assert body["role"] == "EMPLOYEE" and body["employee_code"].startswith("EMP-")
    assert "password" not in body and "password_hash" not in body
    c, s = ctx.container()
    user = c.repos.users.get_by_email("new.person@iitsm.example.com")
    assert user.password_hash if hasattr(user, "password_hash") else True
    assert user._password_hash != "Secret123" and user._password_hash.startswith("$2")
    assert user.check_password("Secret123") and not user.check_password("secret123")
    s.close()


def test_t02_public_registration_cannot_create_admin(ctx):
    r = ctx.client.post("/api/auth/register", json={
        "full_name": "Evil Admin", "email": "evil@iitsm.example.com", "password": "Secret123", "role": "ADMIN"})
    assert r.status_code == 201
    assert r.json()["role"] == "EMPLOYEE"


def test_registration_rejects_duplicate_email_and_weak_password(ctx):
    base = {"full_name": "Dup User", "email": "rahul.verma@iitsm.example.com", "password": "Secret123"}
    assert ctx.client.post("/api/auth/register", json=base).status_code == 409
    weak = {**base, "email": "weak@iitsm.example.com", "password": "short"}
    r = ctx.client.post("/api/auth/register", json=weak)
    assert r.status_code == 422 and r.json()["code"] == "VALIDATION_ERROR"
    assert any(e["field"] == "password" for e in r.json()["errors"])


def test_registration_rejects_invalid_email(ctx):
    r = ctx.client.post("/api/auth/register", json={"full_name": "X Y", "email": "not-an-email", "password": "Secret123"})
    assert r.status_code == 422


def test_t03_login_with_wrong_password_returns_401_without_token(ctx):
    r = ctx.client.post("/api/auth/login", json={"email": "admin@iitsm.example.com", "password": "wrong-password1"})
    assert r.status_code == 401
    assert "access_token" not in r.json() and r.json()["code"] == "AUTHENTICATION_FAILED"
    r = ctx.client.post("/api/auth/login", json={"email": "nobody@iitsm.example.com", "password": "Whatever123"})
    assert r.status_code == 401


def test_login_success_returns_token_and_user_and_is_audited(ctx):
    r = ctx.client.post("/api/auth/login", json={"email": "ADMIN@iitsm.example.com", "password": "Admin@123"})
    assert r.status_code == 200
    data = r.json()
    assert data["token_type"] == "bearer" and data["user"]["role"] == "ADMIN"
    c, s = ctx.container()
    actions = [a.action for a in s.query(AuditLog).all()]
    s.close()
    assert "USER_LOGIN" in actions


def test_failed_login_is_audited(ctx):
    ctx.client.post("/api/auth/login", json={"email": "admin@iitsm.example.com", "password": "nope-nope1"})
    c, s = ctx.container()
    assert any(a.action == "USER_LOGIN_FAILED" for a in s.query(AuditLog).all())
    s.close()


def test_protected_routes_require_a_valid_token(ctx):
    assert ctx.client.get("/api/auth/me").status_code == 401
    assert ctx.client.get("/api/incidents").status_code == 401
    bad = {"Authorization": "Bearer not.a.token"}
    assert ctx.client.get("/api/auth/me", headers=bad).status_code == 401


def test_me_and_profile_update(ctx):
    h = ctx.employee()
    assert ctx.client.get("/api/auth/me", headers=h).json()["email"] == "rahul.verma@iitsm.example.com"
    r = ctx.client.patch("/api/auth/me", headers=h, json={"full_name": "Rahul V. Verma", "department": "Treasury"})
    assert r.status_code == 200 and r.json()["full_name"] == "Rahul V. Verma"
    assert ctx.client.patch("/api/auth/me", headers=h, json={"full_name": "x"}).status_code == 422


def test_change_password_flow(ctx):
    h = ctx.employee()
    bad = ctx.client.post("/api/auth/change-password", headers=h,
                          json={"current_password": "wrong1234", "new_password": "NewSecret1"})
    assert bad.status_code == 401
    ok = ctx.client.post("/api/auth/change-password", headers=h,
                         json={"current_password": "Employee@123", "new_password": "NewSecret1"})
    assert ok.status_code == 200
    assert ctx.client.post("/api/auth/login", json={"email": "rahul.verma@iitsm.example.com", "password": "NewSecret1"}).status_code == 200
    assert ctx.client.post("/api/auth/login", json={"email": "rahul.verma@iitsm.example.com", "password": "Employee@123"}).status_code == 401


def test_deactivated_user_cannot_login_or_use_old_token(ctx):
    h_emp = ctx.employee("divya.nair")
    admin = ctx.admin()
    uid = ctx.user_id("divya.nair")
    assert ctx.client.post(f"/api/users/{uid}/deactivate", headers=admin).status_code == 200
    assert ctx.client.get("/api/auth/me", headers=h_emp).status_code == 401
    r = ctx.client.post("/api/auth/login", json={"email": "divya.nair@iitsm.example.com", "password": "Employee@123"})
    assert r.status_code == 401


def test_password_hash_helpers():
    h = hash_password("Abc12345")
    assert h != "Abc12345" and verify_password("Abc12345", h) and not verify_password("abc12345", h)
    assert verify_password("x", "not-a-hash") is False


def test_health_endpoint(ctx):
    r = ctx.client.get("/health")
    assert r.status_code == 200 and r.json()["database"] is True
