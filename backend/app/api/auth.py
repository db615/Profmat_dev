from fastapi import APIRouter, Depends, Request, Response

from search_prof.backend.app.api.cookies import (
    GOOGLE_COOKIE,
    GOOGLE_PATH,
    REFRESH_COOKIE,
    REFRESH_PATH,
    clear_google_cookie,
    clear_refresh_cookie,
)
from search_prof.backend.app.api.dependencies import (
    AuthDep,
    GoogleDep,
    SettingsDep,
    UserDep,
    limit_auth_requests,
    require_browser_protection,
)
from search_prof.backend.app.core.config import Settings
from search_prof.backend.app.core.database import utcnow
from search_prof.backend.app.schemas import (
    GoogleInput,
    GoogleNonceResponse,
    LoginInput,
    RegisterInput,
    TokenResponse,
    UserRead,
)
from search_prof.backend.app.services.auth import LoginResult

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Authentication"],
    dependencies=[Depends(require_browser_protection), Depends(limit_auth_requests)],
)


def token_response(result: LoginResult, response: Response, settings: Settings) -> TokenResponse:
    response.set_cookie(
        REFRESH_COOKIE,
        result.refresh_token,
        max_age=max(0, int((result.refresh_expires_at - utcnow()).total_seconds())),
        expires=result.refresh_expires_at,
        path=REFRESH_PATH,
        secure=settings.cookie_secure,
        httponly=True,
        samesite=settings.cookie_samesite,
    )
    return TokenResponse(
        access_token=result.access_token,
        expires_in=settings.access_token_minutes * 60,
        user=UserRead.model_validate(result.user),
    )


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(
    body: RegisterInput, response: Response, auth: AuthDep, settings: SettingsDep
) -> TokenResponse:
    result = auth.register(str(body.email), body.password, body.full_name)
    return token_response(result, response, settings)


@router.post("/login", response_model=TokenResponse)
def login(
    body: LoginInput, response: Response, auth: AuthDep, settings: SettingsDep
) -> TokenResponse:
    return token_response(auth.login(str(body.email), body.password), response, settings)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    request: Request, response: Response, auth: AuthDep, settings: SettingsDep
) -> TokenResponse:
    return token_response(auth.refresh(request.cookies.get(REFRESH_COOKIE)), response, settings)


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, auth: AuthDep, settings: SettingsDep) -> None:
    auth.logout(request.cookies.get(REFRESH_COOKIE))
    clear_refresh_cookie(response, settings)
    clear_google_cookie(response, settings)


@router.post("/logout-all", status_code=204)
def logout_all(user: UserDep, response: Response, auth: AuthDep, settings: SettingsDep) -> None:
    auth.logout_all(user.id)
    clear_refresh_cookie(response, settings)
    clear_google_cookie(response, settings)


@router.get("/me", response_model=UserRead)
def me(user: UserDep) -> UserRead:
    return UserRead.model_validate(user)


@router.post("/google/nonce", response_model=GoogleNonceResponse)
def google_nonce(
    response: Response, google: GoogleDep, settings: SettingsDep
) -> GoogleNonceResponse:
    browser_secret, nonce = google.challenge()
    response.set_cookie(
        GOOGLE_COOKIE,
        browser_secret,
        max_age=300,
        path=GOOGLE_PATH,
        secure=settings.cookie_secure,
        httponly=True,
        samesite=settings.cookie_samesite,
    )
    return GoogleNonceResponse(nonce=nonce, client_id=google.client_id)


@router.post("/google", response_model=TokenResponse)
def google_login(
    body: GoogleInput,
    request: Request,
    response: Response,
    google: GoogleDep,
    settings: SettingsDep,
) -> TokenResponse:
    result = google.login(body.id_token, request.cookies.get(GOOGLE_COOKIE))
    clear_google_cookie(response, settings)
    return token_response(result, response, settings)


@router.post("/google/link", response_model=UserRead)
def link_google(
    body: GoogleInput,
    request: Request,
    response: Response,
    user: UserDep,
    google: GoogleDep,
    settings: SettingsDep,
) -> UserRead:
    linked = google.link(user, body.id_token, request.cookies.get(GOOGLE_COOKIE))
    clear_google_cookie(response, settings)
    return UserRead.model_validate(linked)
