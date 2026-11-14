from pathlib import Path
from typing import Literal, Self
from urllib.parse import urlsplit

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    environment: Literal["development", "test", "production"] = "development"
    jwt_private_key_file: Path = Path(".secrets/jwt-private.pem")
    jwt_public_key_file: Path = Path(".secrets/jwt-public.pem")
    jwt_issuer: str = "professor-auth"
    jwt_audience: str = "professor-api"
    access_token_minutes: int = Field(default=15, ge=1, le=60)
    refresh_token_days: int = Field(default=30, ge=1, le=90)
    google_client_id: str | None = None
    cookie_secure: bool = True
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]
    auth_requests_per_minute: int = Field(default=30, ge=1)

    @model_validator(mode="after")
    def validate_browser_security(self) -> Self:
        if (
            self.environment != "test"
            and make_url(self.database_url).drivername != "mariadb+pymysql"
        ):
            raise ValueError("Use a mariadb+pymysql DATABASE_URL for this service")
        for origin in self.allowed_origins:
            parsed = urlsplit(origin)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.path
                or parsed.query
                or parsed.fragment
                or parsed.username
                or parsed.password
                or "*" in origin
            ):
                raise ValueError("ALLOWED_ORIGINS must contain exact HTTP(S) origins")
        if self.cookie_samesite == "none" and not self.cookie_secure:
            raise ValueError("SameSite=None requires secure cookies")
        if self.environment == "production":
            if not self.cookie_secure:
                raise ValueError("Production requires secure cookies")
            if any(not origin.startswith("https://") for origin in self.allowed_origins):
                raise ValueError("Production requires HTTPS origins")
        return self
