from fastapi import Response

from search_prof.backend.app.core.config import Settings

REFRESH_COOKIE = "professor_refresh"
REFRESH_PATH = "/api/v1/auth"
GOOGLE_COOKIE = "professor_google_challenge"
GOOGLE_PATH = "/api/v1/auth/google"


def clear_refresh_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        REFRESH_COOKIE,
        path=REFRESH_PATH,
        secure=settings.cookie_secure,
        httponly=True,
        samesite=settings.cookie_samesite,
    )


def clear_google_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        GOOGLE_COOKIE,
        path=GOOGLE_PATH,
        secure=settings.cookie_secure,
        httponly=True,
        samesite=settings.cookie_samesite,
    )
