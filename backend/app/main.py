from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exception_handlers import http_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from starlette.exceptions import HTTPException as StarletteHTTPException

from search_prof.backend.app.api import auth
from search_prof.backend.app.api.cookies import clear_google_cookie, clear_refresh_cookie
from search_prof.backend.app.api.dependencies import DatabaseDep
from search_prof.backend.app.core.config import Settings
from search_prof.backend.app.core.database import create_database_engine
from search_prof.backend.app.core.security import AccessTokens
from search_prof.backend.app.api import admin


def create_app(
    settings: Settings | None = None,
    engine: Engine | None = None,
    tokens: AccessTokens | None = None,
) -> FastAPI:
    settings = settings or Settings()
    if tokens is None:
        tokens = AccessTokens(
            private_key=settings.jwt_private_key_file.read_text(),
            public_key=settings.jwt_public_key_file.read_text(),
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            lifetime_minutes=settings.access_token_minutes,
        )
    owns_engine = engine is None
    if engine is None:
        engine = create_database_engine(settings.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        if owns_engine:
            engine.dispose()

    app = FastAPI(
        title="Professor Search Auth Service",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None if settings.environment == "production" else "/docs",
        redoc_url=None,
    )
    app.state.settings = settings
    app.state.tokens = tokens
    app.state.session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type", "X-CSRF-Protection"],
    )

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
            response.headers["Pragma"] = "no-cache"
        return response

    @app.exception_handler(StarletteHTTPException)
    async def handle_auth_error(request: Request, error: StarletteHTTPException):
        response = await http_exception_handler(request, error)
        if request.url.path == "/api/v1/auth/refresh" and error.status_code == 401:
            clear_refresh_cookie(response, settings)
        if request.url.path in {"/api/v1/auth/google", "/api/v1/auth/google/link"}:
            clear_google_cookie(response, settings)
        return response

    @app.get("/health/live", tags=["Health"])
    def live() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready", tags=["Health"])
    def ready(session: DatabaseDep) -> dict[str, str]:
        try:
            session.execute(text("SELECT 1"))
        except SQLAlchemyError as error:
            raise HTTPException(status_code=503, detail="Database is unavailable") from error
        return {"status": "ready"}

    @app.get("/.well-known/jwks.json", tags=["Service Identity"])
    def jwks(response: Response) -> dict:
        response.headers["Cache-Control"] = "public, max-age=300"
        return tokens.jwks()

    app.include_router(auth.router)
    app.include_router(admin.router)
    return app
