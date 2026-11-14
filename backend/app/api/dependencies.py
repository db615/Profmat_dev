from collections.abc import Iterator
from datetime import timedelta
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, Header, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from search_prof.backend.app.core.config import Settings
from search_prof.backend.app.core.database import utcnow
from search_prof.backend.app.core.security import hash_secret
from search_prof.backend.app.models import User
from search_prof.backend.app.repositories.auth import AuthRepository
from search_prof.backend.app.services.auth import AuthService, invalid_credentials
from search_prof.backend.app.services.google import GoogleLogin, GoogleVerifier, verify_google_token

bearer = HTTPBearer(auto_error=False)


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_session(request: Request) -> Iterator[Session]:
    with request.app.state.session_factory() as session:
        yield session


SettingsDep = Annotated[Settings, Depends(get_settings)]
DatabaseDep = Annotated[Session, Depends(get_session)]


def require_browser_protection(
    request: Request,
    settings: SettingsDep,
    x_csrf_protection: Annotated[str | None, Header(description="Use the value 1")] = None,
) -> None:
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    origin = request.headers.get("origin")
    if origin is not None and origin not in settings.allowed_origins:
        raise HTTPException(status_code=403, detail="Origin is not allowed")
    if x_csrf_protection != "1":
        raise HTTPException(status_code=403, detail="X-CSRF-Protection: 1 is required")


def limit_auth_requests(request: Request, session: DatabaseDep, settings: SettingsDep) -> None:
    if request.method != "POST":
        return
    now = utcnow()
    client_ip = request.client.host if request.client else "unknown"
    bucket = hash_secret(f"auth:{client_ip}:{int(now.timestamp()) // 60}")
    attempts = AuthRepository(session).hit_rate_limit(bucket, now + timedelta(minutes=2))
    if attempts > settings.auth_requests_per_minute:
        raise HTTPException(
            status_code=429,
            detail="Too many authentication requests",
            headers={"Retry-After": str(60 - now.second)},
        )


def get_auth_service(request: Request, session: DatabaseDep, settings: SettingsDep) -> AuthService:
    return AuthService(session, request.app.state.tokens, settings.refresh_token_days)


AuthDep = Annotated[AuthService, Depends(get_auth_service)]


def get_google_verifier() -> GoogleVerifier:
    return verify_google_token


def get_google_service(
    auth: AuthDep,
    settings: SettingsDep,
    verifier: Annotated[GoogleVerifier, Depends(get_google_verifier)],
) -> GoogleLogin:
    return GoogleLogin(auth, settings.google_client_id, verifier)


GoogleDep = Annotated[GoogleLogin, Depends(get_google_service)]


def current_user(
    request: Request,
    session: DatabaseDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> User:
    if credentials is None:
        raise invalid_credentials()
    try:
        claims = request.app.state.tokens.verify(credentials.credentials)
        user_id = UUID(claims["sub"])
    except (jwt.InvalidTokenError, ValueError, KeyError) as error:
        raise invalid_credentials() from error
    user = session.get(User, user_id)
    if user is None or not user.is_active:
        raise invalid_credentials()
    return user


UserDep = Annotated[User, Depends(current_user)]


def require_admin(user: UserDep) -> User:
    if user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Administrator role required")
    return user


AdminDep = Annotated[User, Depends(require_admin)]
