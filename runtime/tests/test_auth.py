import os

from fastapi.testclient import TestClient

os.environ.setdefault("FAST_HARNESS_PASSWORD_ZHAOJINDONG", "test-password-zhaojindong")
os.environ.setdefault("FAST_HARNESS_PASSWORD_USER02", "test-password-user02")

from src.core import auth
from src.main import app


def test_auth_token_is_valid_for_one_week(monkeypatch):
    monkeypatch.setattr(auth.settings, "auth_secret", "test-secret")
    token = auth.create_session_token("zhaojindong", now=1000)

    assert auth.verify_session_token(token, now=1000 + auth.SESSION_TTL_SECONDS - 1) == "zhaojindong"
    assert auth.verify_session_token(token, now=1000 + auth.SESSION_TTL_SECONDS + 1) is None


def test_home_redirects_to_login_when_unauthenticated():
    client = TestClient(app)

    response = client.get("/", follow_redirects=False)
    login = client.get("/login")

    assert response.status_code == 303
    assert response.headers["location"] == "/login"
    assert login.status_code == 200
    assert 'id="loginForm"' in login.text


def test_api_requires_login_when_unauthenticated():
    client = TestClient(app)

    response = client.get("/api/me")

    assert response.status_code == 401


def test_login_sets_cookie_and_allows_home():
    client = TestClient(app)
    user = auth.settings.get_user("zhaojindong")

    login = client.post(
        "/api/login",
        json={"user_id": "zhaojindong", "password": user["password"]},
    )
    home = client.get("/", follow_redirects=False)
    me = client.get("/api/me")

    assert login.status_code == 200
    assert auth.SESSION_COOKIE_NAME in login.cookies
    assert home.status_code == 200
    assert me.status_code == 200
    assert me.json()["user"]["id"] == "zhaojindong"


def test_users_endpoint_does_not_expose_passwords():
    client = TestClient(app)

    response = client.get("/api/users")

    assert response.status_code == 200
    assert "password" not in response.text


def test_usage_stats_requires_admin_role():
    client = TestClient(app)
    user = auth.settings.get_user("user02")

    login = client.post(
        "/api/login",
        json={"user_id": "user02", "password": user["password"]},
    )
    response = client.get("/api/usage-stats")

    assert login.status_code == 200
    assert response.status_code == 403
