import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

import jwt
import pytest
from fastapi import HTTPException
from google.auth.exceptions import TransportError
from sqlalchemy import select

from search_prof.backend.app.core.database import utcnow
from search_prof.backend.app.models import GoogleChallenge, User
from search_prof.backend.app.services.auth import AuthService
from search_prof.backend.app.services.google import GoogleLogin, verify_google_token


@pytest.fixture
def google(session, tokens):
    return GoogleLogin(AuthService(session, tokens), "test-client", Mock())


def prepare_google(google, **overrides):
    browser_secret, nonce = google.challenge()
    google.verifier.return_value = {
        "sub": "google-subject-123",
        "email": "Person@example.com",
        "email_verified": True,
        "nonce": nonce,
        "name": "Example Person",
        **overrides,
    }
    return browser_secret


def test_google_registers_and_reuses_subject(google, session):
    first = google.login("google-id-token", prepare_google(google))
    second = google.login("google-id-token", prepare_google(google))
    assert first.user.id == second.user.id
    assert first.user.email == "person@example.com"
    assert first.user.email_verified
    assert first.user.password_hash is None
    assert first.user.role == "USER"
    assert len(session.scalars(select(User)).all()) == 1
    google.verifier.assert_called_with("google-id-token", "test-client")


@pytest.mark.parametrize(
    "overrides",
    [
        {"email_verified": False},
        {"email_verified": "true"},
        {"nonce": "wrong-nonce"},
        {"azp": "another-client"},
        {"sub": ""},
        {"email": "invalid-email"},
    ],
)
def test_invalid_google_identity_is_rejected(google, overrides):
    with pytest.raises(HTTPException) as error:
        google.login("google-id-token", prepare_google(google, **overrides))
    assert error.value.status_code == 401


def test_google_nonce_is_one_time_and_browser_bound(google):
    browser_secret = prepare_google(google)
    with pytest.raises(HTTPException):
        google.login("google-id-token", "different-browser")
    google.login("google-id-token", browser_secret)
    with pytest.raises(HTTPException):
        google.login("google-id-token", browser_secret)


def test_expired_google_challenge_is_rejected(google, session):
    browser_secret = prepare_google(google)
    challenge = session.scalar(select(GoogleChallenge))
    challenge.expires_at = utcnow() - timedelta(seconds=1)
    session.commit()
    with pytest.raises(HTTPException):
        google.login("google-id-token", browser_secret)
    google.verifier.assert_not_called()


def test_google_does_not_automatically_link_password_accounts(google):
    local = google.auth.register("person@example.com", "long test password")
    with pytest.raises(HTTPException) as error:
        google.login("google-id-token", prepare_google(google))
    assert error.value.status_code == 409
    assert local.user.google_sub is None
    linked = google.link(local.user, "google-id-token", prepare_google(google))
    assert linked.google_sub == "google-subject-123"
    assert linked.email_verified
    assert google.login("google-id-token", prepare_google(google)).user.id == local.user.id


def test_link_requires_matching_email(google):
    local = google.auth.register("another@example.com", "long test password")
    with pytest.raises(HTTPException) as error:
        google.link(local.user, "google-id-token", prepare_google(google))
    assert error.value.status_code == 409


def test_disabled_google_account_is_rejected(google, session):
    result = google.login("google-id-token", prepare_google(google))
    result.user.is_active = False
    session.commit()
    with pytest.raises(HTTPException):
        google.login("google-id-token", prepare_google(google))


def test_unconfigured_google_is_explicitly_disabled(session, tokens):
    with pytest.raises(HTTPException) as error:
        GoogleLogin(AuthService(session, tokens), None)
    assert error.value.status_code == 503


@patch("app.services.google.id_token.verify_oauth2_token")
def test_google_verification_uses_configured_audience(verifier):
    verifier.return_value = {"sub": "google-subject"}
    assert verify_google_token("credential", "client-id") == {"sub": "google-subject"}
    assert verifier.call_args.kwargs["audience"] == "client-id"


@pytest.mark.parametrize("failure, code", [(ValueError("invalid"), 401), (TransportError(), 503)])
@patch("app.services.google.id_token.verify_oauth2_token")
def test_google_verification_handles_failures(verifier, failure, code):
    verifier.side_effect = failure
    with pytest.raises(HTTPException) as error:
        verify_google_token("credential", "client-id")
    assert error.value.status_code == code


@pytest.mark.parametrize(
    "changes, valid",
    [
        ({}, True),
        ({"aud": "another-client"}, False),
        ({"iss": "https://attacker.example"}, False),
        ({"exp": 1}, False),
    ],
)
@patch("app.services.google.GoogleRequest")
def test_google_library_verifies_signed_tokens(request_factory, signing_keys, changes, valid):
    private_key, public_key = signing_keys
    request_factory.return_value.return_value = SimpleNamespace(
        status=200, data=json.dumps({"test-key": public_key}).encode()
    )
    now = datetime.now(UTC)
    credential = jwt.encode(
        {
            "iss": "https://accounts.google.com",
            "aud": "client-id",
            "iat": now,
            "exp": now + timedelta(minutes=5),
            "sub": "test-google-subject",
            **changes,
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )
    if valid:
        assert verify_google_token(credential, "client-id")["sub"] == "test-google-subject"
    else:
        with pytest.raises(HTTPException) as error:
            verify_google_token(credential, "client-id")
        assert error.value.status_code == 401
    assert request_factory.return_value.call_args.kwargs["timeout"] == 10
