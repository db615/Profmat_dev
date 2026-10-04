from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from search_prof.backend.app.core.database import utcnow
from search_prof.backend.app.core.security import AccessTokens, hash_password, hash_secret, new_secret, verify_password
from search_prof.backend.app.models import RefreshSession, User
from search_prof.backend.app.repositories.auth import AuthRepository

DUMMY_PASSWORD_HASH = hash_password(new_secret())


def invalid_credentials() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


@dataclass
class LoginResult:
    user: User
    access_token: str
    refresh_token: str
    refresh_expires_at: datetime


class AuthService:
    def __init__(self, session: Session, tokens: AccessTokens, refresh_days: int = 30) -> None:
        self.session = session
        self.repository = AuthRepository(session)
        self.tokens = tokens
        self.refresh_days = refresh_days

    def start_session(
        self,
        user: User,
        family_id: UUID | None = None,
        expires_at: datetime | None = None,
    ) -> LoginResult:
        secret = new_secret()
        expires_at = expires_at or utcnow() + timedelta(days=self.refresh_days)
        self.session.add(
            RefreshSession(
                user_id=user.id,
                family_id=family_id or uuid4(),
                token_hash=hash_secret(secret),
                expires_at=expires_at,
            )
        )
        access_token = self.tokens.issue(str(user.id), user.role)
        self.session.commit()
        return LoginResult(user, access_token, secret, expires_at)

    def register(self, email: str, password: str, full_name: str | None = None) -> LoginResult:
        if self.repository.user_by_email(email):
            raise HTTPException(status_code=409, detail="Email is already registered")
        user = User(email=email, password_hash=hash_password(password), full_name=full_name)
        self.session.add(user)
        try:
            self.session.flush()
            return self.start_session(user)
        except IntegrityError as error:
            self.session.rollback()
            raise HTTPException(status_code=409, detail="Email is already registered") from error

    def login(self, email: str, password: str) -> LoginResult:
        user = self.repository.user_by_email(email)
        encoded = user.password_hash if user and user.password_hash else DUMMY_PASSWORD_HASH
        password_valid = verify_password(password, encoded)
        if not user or not user.password_hash or not password_valid or not user.is_active:
            raise invalid_credentials()
        return self.start_session(user)

    def refresh(self, secret: str | None) -> LoginResult:
        if not secret or len(secret) > 256:
            raise invalid_credentials()
        token_hash = hash_secret(secret)
        refresh = self.repository.refresh_by_hash(token_hash)
        if refresh is None:
            raise invalid_credentials()
        user = self.repository.lock_user(refresh.user_id)
        refresh = self.repository.refresh_by_hash(token_hash)
        if not user or not user.is_active or refresh is None:
            raise invalid_credentials()
        if refresh.used_at is not None or refresh.revoked_at is not None:
            self.repository.revoke_family(refresh.family_id)
            self.session.commit()
            raise invalid_credentials()
        if refresh.expires_at <= utcnow():
            raise invalid_credentials()
        refresh.used_at = utcnow()
        return self.start_session(user, refresh.family_id, refresh.expires_at)

    def logout(self, secret: str | None) -> None:
        if secret and len(secret) <= 256:
            refresh = self.repository.refresh_by_hash(hash_secret(secret))
            if refresh:
                self.repository.lock_user(refresh.user_id)
                self.repository.revoke_family(refresh.family_id)
                self.session.commit()

    def logout_all(self, user_id: UUID) -> None:
        self.repository.lock_user(user_id)
        self.repository.revoke_all(user_id)
        self.session.commit()
