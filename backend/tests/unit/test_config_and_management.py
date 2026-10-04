from datetime import timedelta
from stat import S_IMODE
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select

from search_prof.backend.app.core.config import Settings
from search_prof.backend.app.core.database import utcnow
from search_prof.backend.app.core.security import AccessTokens, hash_secret, new_secret
from search_prof.backend.app.manage import cleanup, init_dev, init_docker, promote_admin
from search_prof.backend.app.models import RefreshSession
from search_prof.backend.app.services.auth import AuthService


def settings(**changes):
    return Settings(
        _env_file=None,
        **{
            "database_url": "mariadb+pymysql://localhost/Professorsdb",
            "environment": "production",
            "allowed_origins": ["https://professors.example"],
            **changes,
        },
    )


def test_production_requires_secure_browser_configuration():
    assert settings().cookie_secure
    for changes in [
        {"cookie_secure": False},
        {"allowed_origins": ["http://professors.example"]},
        {"allowed_origins": ["https://*.example"]},
        {"allowed_origins": ["https://professors.example/"]},
        {"database_url": "sqlite:///test.db"},
        {"database_url": "postgresql+psycopg://localhost/professor_auth"},
    ]:
        with pytest.raises(ValidationError):
            settings(**changes)
    with pytest.raises(ValidationError):
        settings(environment="development", cookie_samesite="none", cookie_secure=False)


def test_local_setup_keeps_secrets_private_and_does_not_overwrite(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    init_dev(tmp_path, db_port=3307, api_port=8001)
    env_path = tmp_path / ".env"
    private_path = tmp_path / ".secrets/jwt-private.pem"
    public_path = tmp_path / ".secrets/jwt-public.pem"
    assert S_IMODE(env_path.stat().st_mode) == 0o600
    assert S_IMODE(private_path.stat().st_mode) == 0o600
    configured = Settings(_env_file=env_path)
    assert configured.database_url.startswith("mariadb+pymysql://")
    assert "localhost:3307/Professorsdb?charset=utf8mb4" in configured.database_url
    assert "http://localhost:8001" in configured.allowed_origins
    assert not configured.cookie_secure
    tokens = AccessTokens(private_path.read_text(), public_path.read_text(), "issuer", "audience")
    assert tokens.verify(tokens.issue("user-id", "USER"))["sub"] == "user-id"
    previous = env_path.read_bytes()
    with pytest.raises(SystemExit, match="not modified"):
        init_dev(tmp_path, db_port=3307, api_port=8001)
    assert env_path.read_bytes() == previous


def test_docker_setup_is_repeatable_without_rotating_credentials(tmp_path):
    init_docker(tmp_path, db_port=3306, api_port=8000)
    files = [
        tmp_path / ".env",
        tmp_path / ".secrets/jwt-private.pem",
        tmp_path / ".secrets/jwt-public.pem",
    ]
    original = {path: path.read_bytes() for path in files}
    init_docker(tmp_path, db_port=3307, api_port=8001)
    assert {path: path.read_bytes() for path in files} == original


def test_docker_setup_refuses_to_replace_partial_configuration(tmp_path):
    init_docker(tmp_path, db_port=3306, api_port=8000)
    env_path = tmp_path / ".env"
    original = env_path.read_bytes()
    (tmp_path / ".secrets/jwt-public.pem").unlink()
    with pytest.raises(SystemExit, match="not modified"):
        init_docker(tmp_path, db_port=3306, api_port=8000)
    assert env_path.read_bytes() == original
    assert not (tmp_path / ".secrets/jwt-public.pem").exists()


def test_admin_promotion_revokes_existing_refresh_tokens(session, tokens):
    auth = AuthService(session, tokens)
    result = auth.register("admin@example.com", "long test password")
    promote_admin(session, "ADMIN@example.com")
    assert result.user.role == "ADMIN"
    with pytest.raises(HTTPException):
        auth.refresh(result.refresh_token)


def test_cleanup_preserves_replay_detection_records(session, tokens):
    auth = AuthService(session, tokens)
    initial = auth.register("person@example.com", "long test password")
    rotated = auth.refresh(initial.refresh_token)
    session.add(
        RefreshSession(
            user_id=initial.user.id,
            family_id=uuid4(),
            token_hash=hash_secret(new_secret()),
            expires_at=utcnow() - timedelta(minutes=1),
        )
    )
    session.commit()
    cleanup(session)
    assert len(session.scalars(select(RefreshSession)).all()) == 2
    with pytest.raises(HTTPException):
        auth.refresh(initial.refresh_token)
    with pytest.raises(HTTPException):
        auth.refresh(rotated.refresh_token)
