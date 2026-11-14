from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from search_prof.backend.app.api.cookies import GOOGLE_COOKIE, REFRESH_COOKIE
from search_prof.backend.app.api.dependencies import get_google_verifier
from search_prof.backend.app.core.config import Settings
from search_prof.backend.app.main import create_app
from search_prof.backend.app.models import User

PASSWORD = "long test password"
REGISTER = {"email": "person@example.com", "password": PASSWORD, "full_name": "Example Person"}


@pytest.fixture
def app(database, tokens):
    settings = Settings(
        _env_file=None,
        environment="test",
        database_url="sqlite+pysqlite://",
        cookie_secure=False,
        google_client_id="test-client",
    )
    return create_app(settings, database, tokens)


@pytest.fixture
def client(app):
    with TestClient(app, headers={"X-CSRF-Protection": "1"}) as client:
        yield client


def authorization(response):
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_register_login_and_private_profile(client):
    response = client.post("/api/v1/auth/register", json=REGISTER)
    assert response.status_code == 201
    assert response.json()["expires_in"] == 900
    assert response.json()["user"]["role"] == "USER"
    assert "refresh_token" not in response.json()
    assert "password_hash" not in response.text
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=lax" in response.headers["set-cookie"]
    assert "Path=/api/v1/auth" in response.headers["set-cookie"]
    assert response.headers["cache-control"] == "no-store"
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/auth/me", headers=authorization(response)).status_code == 200
    login = client.post(
        "/api/v1/auth/login", json={"email": "PERSON@example.com", "password": PASSWORD}
    )
    assert login.status_code == 200
    assert login.json()["user"]["id"] == response.json()["user"]["id"]


def test_registration_validates_password_and_cannot_assign_admin(client):
    for body in [{**REGISTER, "password": "short"}, {**REGISTER, "role": "ADMIN"}]:
        assert client.post("/api/v1/auth/register", json=body).status_code == 422
    assert client.post("/api/v1/auth/register", json=REGISTER).status_code == 201
    assert (
        client.post(
            "/api/v1/auth/register", json={**REGISTER, "email": "PERSON@example.com"}
        ).status_code
        == 409
    )


def test_browser_csrf_protection(client):
    client.headers.pop("X-CSRF-Protection")
    assert client.post("/api/v1/auth/register", json=REGISTER).status_code == 403
    assert (
        client.post(
            "/api/v1/auth/register",
            json=REGISTER,
            headers={"Origin": "https://attacker.example", "X-CSRF-Protection": "1"},
        ).status_code
        == 403
    )
    response = client.post(
        "/api/v1/auth/register",
        json=REGISTER,
        headers={"Origin": "http://localhost:3000", "X-CSRF-Protection": "1"},
    )
    assert response.status_code == 201
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert response.headers["access-control-allow-credentials"] == "true"


def test_refresh_cookie_rotation_and_replay(client):
    client.post("/api/v1/auth/register", json=REGISTER)
    initial = client.cookies.get(REFRESH_COOKIE)
    assert client.post("/api/v1/auth/refresh").status_code == 200
    rotated = client.cookies.get(REFRESH_COOKIE)
    assert initial != rotated
    for secret in [initial, rotated]:
        response = client.post(
            "/api/v1/auth/refresh", headers={"Cookie": f"{REFRESH_COOKIE}={secret}"}
        )
        assert response.status_code == 401
        assert "Max-Age=0" in response.headers["set-cookie"]


def test_logout_and_logout_all(client):
    registered = client.post("/api/v1/auth/register", json=REGISTER)
    assert client.post("/api/v1/auth/logout-all").status_code == 401
    response = client.post("/api/v1/auth/logout-all", headers=authorization(registered))
    assert response.status_code == 204
    assert response.content == b""
    assert client.post("/api/v1/auth/refresh").status_code == 401
    assert client.post("/api/v1/auth/logout").status_code == 204


def test_roles_are_checked_against_database(client, session):
    registered = client.post("/api/v1/auth/register", json=REGISTER)
    headers = authorization(registered)
    assert client.get("/api/v1/admin/users").status_code == 401
    assert client.get("/api/v1/admin/users", headers=headers).status_code == 403
    user = session.scalar(select(User))
    user.role = "ADMIN"
    session.commit()
    response = client.get("/api/v1/admin/users", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert "password_hash" not in response.text
    assert client.get("/api/v1/admin/users?limit=101", headers=headers).status_code == 422
    user.is_active = False
    session.commit()
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401


def test_google_login_via_nonce_cookie(client, app):
    challenge = client.post("/api/v1/auth/google/nonce")
    assert challenge.status_code == 200
    assert "HttpOnly" in challenge.headers["set-cookie"]
    verifier = Mock(
        return_value={
            "sub": "google-subject",
            "email": "person@example.com",
            "email_verified": True,
            "nonce": challenge.json()["nonce"],
        }
    )
    app.dependency_overrides[get_google_verifier] = lambda: verifier
    response = client.post("/api/v1/auth/google", json={"id_token": "google-token"})
    assert response.status_code == 200
    assert response.json()["user"]["email_verified"]
    assert client.cookies.get(GOOGLE_COOKIE) is None
    assert client.cookies.get(REFRESH_COOKIE)
    assert client.post("/api/v1/auth/google", json={"id_token": "google-token"}).status_code == 401


def test_google_requires_configuration(client, app):
    app.state.settings.google_client_id = None
    assert client.post("/api/v1/auth/google/nonce").status_code == 503


def test_shared_database_rate_limit(client, app):
    app.state.settings.auth_requests_per_minute = 2
    for _ in range(2):
        assert (
            client.post("/api/v1/auth/login", json=REGISTER | {"full_name": None}).status_code
            == 422
        )
    response = client.post(
        "/api/v1/auth/login", json={"email": REGISTER["email"], "password": PASSWORD}
    )
    assert response.status_code == 429
    assert 1 <= int(response.headers["retry-after"]) <= 60


def test_health_and_public_keys(client):
    assert client.get("/health/live").json() == {"status": "ok"}
    assert client.get("/health/ready").json() == {"status": "ready"}
    response = client.get("/.well-known/jwks.json")
    assert response.status_code == 200
    assert response.json()["keys"][0]["alg"] == "RS256"
    assert "d" not in response.json()["keys"][0]
    assert client.get("/openapi.json").status_code == 200
