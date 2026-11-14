from datetime import UTC, datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from search_prof.backend.app.core.database import utcnow
from search_prof.backend.app.core.security import hash_secret
from search_prof.backend.app.models import RefreshSession, User
from search_prof.backend.app.services.auth import AuthService


@pytest.fixture
def service(session, tokens):
    return AuthService(session, tokens)


def test_registration_persists_user_and_hashed_session(service, session):
    result = service.register("person@example.com", "long test password")
    user = session.scalar(select(User))
    refresh = session.scalar(select(RefreshSession))
    assert user.id == result.user.id
    assert user.role == "USER"
    assert not user.email_verified
    assert user.password_hash != "long test password"
    assert refresh.token_hash == hash_secret(result.refresh_token)
    assert service.tokens.verify(result.access_token)["sub"] == str(user.id)


def test_duplicate_registration_is_rejected(service):
    service.register("person@example.com", "long test password")
    with pytest.raises(HTTPException) as error:
        service.register("person@example.com", "a different password")
    assert error.value.status_code == 409


def test_login_has_generic_errors(service):
    service.register("person@example.com", "long test password")
    assert service.login("person@example.com", "long test password").user.email
    for email in ["person@example.com", "unknown@example.com"]:
        with pytest.raises(HTTPException) as error:
            service.login(email, "incorrect password")
        assert error.value.status_code == 401
        assert error.value.detail == "Invalid credentials"


def test_refresh_rotates_and_replay_revokes_replacement(service):
    initial = service.register("person@example.com", "long test password")
    rotated = service.refresh(initial.refresh_token)
    assert rotated.refresh_token != initial.refresh_token
    assert rotated.refresh_expires_at == initial.refresh_expires_at
    for secret in [initial.refresh_token, rotated.refresh_token]:
        with pytest.raises(HTTPException) as error:
            service.refresh(secret)
        assert error.value.status_code == 401


def test_session_timestamp_round_trip_preserves_utc_and_microseconds(service, session):
    service.register("person@example.com", "long test password")
    refresh = session.scalar(select(RefreshSession))
    expires_at = datetime(
        2030, 1, 2, 3, 4, 5, 123456, tzinfo=timezone(timedelta(hours=5, minutes=45))
    )
    refresh.expires_at = expires_at
    session.commit()
    session.expire_all()
    stored = session.scalar(select(RefreshSession)).expires_at
    assert stored == expires_at.astimezone(UTC)
    assert stored.microsecond == 123456


def test_expired_refresh_is_rejected(service, session):
    result = service.register("person@example.com", "long test password")
    refresh = session.scalar(select(RefreshSession))
    refresh.expires_at = utcnow() - timedelta(seconds=1)
    session.commit()
    with pytest.raises(HTTPException):
        service.refresh(result.refresh_token)


def test_logout_revokes_only_current_family(service):
    initial = service.register("person@example.com", "long test password")
    second_device = service.login("person@example.com", "long test password")
    rotated = service.refresh(initial.refresh_token)
    service.logout(initial.refresh_token)
    with pytest.raises(HTTPException):
        service.refresh(rotated.refresh_token)
    assert service.refresh(second_device.refresh_token)


def test_logout_all_revokes_all_devices(service):
    first = service.register("person@example.com", "long test password")
    second = service.login("person@example.com", "long test password")
    service.logout_all(first.user.id)
    for secret in [first.refresh_token, second.refresh_token]:
        with pytest.raises(HTTPException):
            service.refresh(secret)


def test_disabled_user_cannot_login_or_refresh(service, session):
    result = service.register("person@example.com", "long test password")
    result.user.is_active = False
    session.commit()
    with pytest.raises(HTTPException):
        service.login("person@example.com", "long test password")
    with pytest.raises(HTTPException):
        service.refresh(result.refresh_token)
