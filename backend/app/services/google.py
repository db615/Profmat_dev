import secrets
from collections.abc import Callable
from datetime import timedelta
from functools import partial

from fastapi import HTTPException
from google.auth.exceptions import GoogleAuthError, TransportError
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from search_prof.backend.app.core.database import utcnow
from search_prof.backend.app.core.security import hash_secret, new_secret
from search_prof.backend.app.models import GoogleChallenge, User
from search_prof.backend.app.schemas import GoogleIdentity
from search_prof.backend.app.services.auth import AuthService, LoginResult, invalid_credentials

GoogleVerifier = Callable[[str, str], dict]


def verify_google_token(credential: str, client_id: str) -> dict:
    try:
        return id_token.verify_oauth2_token(
            credential,
            partial(GoogleRequest(), timeout=10),
            audience=client_id,
        )
    except TransportError as error:
        raise HTTPException(status_code=503, detail="Google verification is unavailable") from error
    except (ValueError, GoogleAuthError) as error:
        raise invalid_credentials() from error


class GoogleLogin:
    def __init__(
        self,
        auth: AuthService,
        client_id: str | None,
        verifier: GoogleVerifier = verify_google_token,
    ) -> None:
        if not client_id:
            raise HTTPException(status_code=503, detail="Google login is not configured")
        self.auth = auth
        self.client_id = client_id
        self.verifier = verifier

    def challenge(self) -> tuple[str, str]:
        browser_secret = new_secret()
        nonce = new_secret()
        self.auth.session.add(
            GoogleChallenge(
                token_hash=hash_secret(browser_secret),
                nonce_hash=hash_secret(nonce),
                expires_at=utcnow() + timedelta(minutes=5),
            )
        )
        self.auth.session.commit()
        return browser_secret, nonce

    def identity(self, credential: str, browser_secret: str | None) -> GoogleIdentity:
        if not browser_secret or len(browser_secret) > 256:
            raise invalid_credentials()
        challenge = self.auth.repository.consume_google_challenge(hash_secret(browser_secret))
        if challenge is None or challenge.expires_at <= utcnow():
            raise invalid_credentials()
        claims = self.verifier(credential, self.client_id)
        if claims.get("email_verified") is not True:
            raise invalid_credentials()
        if claims.get("azp", self.client_id) != self.client_id:
            raise invalid_credentials()
        try:
            identity = GoogleIdentity.model_validate(claims)
        except ValidationError as error:
            raise invalid_credentials() from error
        if not secrets.compare_digest(hash_secret(identity.nonce), challenge.nonce_hash):
            raise invalid_credentials()
        identity.email = identity.email.lower()
        return identity

    def login(self, credential: str, browser_secret: str | None) -> LoginResult:
        identity = self.identity(credential, browser_secret)
        user = self.auth.repository.user_by_google_sub(identity.sub)
        if user:
            if not user.is_active:
                raise invalid_credentials()
            return self.auth.start_session(user)
        if self.auth.repository.user_by_email(identity.email):
            raise HTTPException(
                status_code=409,
                detail="Sign in to your existing account and link Google first",
            )
        user = User(
            email=identity.email,
            full_name=identity.name,
            google_sub=identity.sub,
            email_verified=True,
        )
        self.auth.session.add(user)
        try:
            self.auth.session.flush()
            return self.auth.start_session(user)
        except IntegrityError as error:
            self.auth.session.rollback()
            raise HTTPException(
                status_code=409, detail="Account already exists; sign in again"
            ) from error

    def link(self, user: User, credential: str, browser_secret: str | None) -> User:
        identity = self.identity(credential, browser_secret)
        locked_user = self.auth.repository.lock_user(user.id)
        if locked_user is None or not locked_user.is_active:
            raise invalid_credentials()
        if identity.email != locked_user.email:
            raise HTTPException(
                status_code=409, detail="Google email must match your account email"
            )
        existing = self.auth.repository.user_by_google_sub(identity.sub)
        if existing and existing.id != locked_user.id:
            raise HTTPException(status_code=409, detail="Google account is already linked")
        if locked_user.google_sub and locked_user.google_sub != identity.sub:
            raise HTTPException(
                status_code=409, detail="A different Google account is already linked"
            )
        locked_user.google_sub = identity.sub
        locked_user.email_verified = True
        try:
            self.auth.session.commit()
        except IntegrityError as error:
            self.auth.session.rollback()
            raise HTTPException(
                status_code=409, detail="Google account is already linked"
            ) from error
        return locked_user
