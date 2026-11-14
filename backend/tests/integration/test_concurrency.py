from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import sessionmaker

from search_prof.backend.app.core.database import utcnow
from search_prof.backend.app.core.security import hash_secret
from search_prof.backend.app.repositories.auth import AuthRepository
from search_prof.backend.app.services.auth import AuthService
from search_prof.backend.app.services.google import GoogleLogin


@pytest.fixture
def sessions(database):
    if database.dialect.name != "mariadb":
        pytest.skip("Row-locking checks require pytest --mariadb")
    return sessionmaker(bind=database, expire_on_commit=False)


def test_connections_use_read_committed(sessions):
    with sessions() as session:
        assert session.connection().get_isolation_level() == "READ COMMITTED"


def test_concurrent_rate_limit_counts_every_attempt(sessions):
    barrier = Barrier(4)
    bucket_hash = hash_secret("concurrent-rate-limit-test")
    expires_at = utcnow() + timedelta(minutes=2)

    def increment():
        with sessions() as session:
            barrier.wait(timeout=10)
            return AuthRepository(session).hit_rate_limit(bucket_hash, expires_at)

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(increment) for attempt in range(4)]
        assert sorted(future.result() for future in futures) == [1, 2, 3, 4]


def test_concurrent_refresh_has_one_winner_and_revokes_replay(sessions, tokens):
    with sessions() as session:
        initial = AuthService(session, tokens).register("person@example.com", "long test password")
    barrier = Barrier(2)

    def rotate():
        with sessions() as session:
            barrier.wait(timeout=10)
            try:
                return AuthService(session, tokens).refresh(initial.refresh_token)
            except HTTPException as error:
                return error.status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: rotate(), range(2)))
    assert results.count(401) == 1
    winner = next(result for result in results if result != 401)
    with sessions() as session, pytest.raises(HTTPException) as error:
        AuthService(session, tokens).refresh(winner.refresh_token)
    assert error.value.status_code == 401


def test_concurrent_google_challenge_is_consumed_once(sessions, tokens):
    with sessions() as session:
        browser_secret, nonce = GoogleLogin(AuthService(session, tokens), "client-id").challenge()
    barrier = Barrier(2)

    def verify(credential, client_id):
        return {
            "sub": "google-subject",
            "email": "person@example.com",
            "email_verified": True,
            "nonce": nonce,
        }

    def login():
        with sessions() as session:
            barrier.wait(timeout=10)
            try:
                GoogleLogin(AuthService(session, tokens), "client-id", verify).login(
                    "credential", browser_secret
                )
                return 200
            except HTTPException as error:
                return error.status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(lambda _: login(), range(2))) == [200, 401]


def test_concurrent_registration_enforces_unique_email(sessions, tokens):
    barrier = Barrier(2)

    def register():
        with sessions() as session:
            barrier.wait(timeout=10)
            try:
                AuthService(session, tokens).register("person@example.com", "long test password")
                return 201
            except HTTPException as error:
                return error.status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(lambda _: register(), range(2))) == [201, 409]
