from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator

FullName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class EmailInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower()


class RegisterInput(EmailInput):
    password: str = Field(min_length=12, max_length=128)
    full_name: FullName | None = None


class LoginInput(EmailInput):
    password: str = Field(min_length=1, max_length=128)


class GoogleInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id_token: str = Field(min_length=1, max_length=16384)


class GoogleIdentity(BaseModel):
    sub: str = Field(min_length=1, max_length=255)
    email: EmailStr
    nonce: str = Field(min_length=1, max_length=256)
    name: FullName | None = None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str | None
    role: Literal["USER", "ADMIN"]
    is_active: bool
    email_verified: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    user: UserRead


class GoogleNonceResponse(BaseModel):
    nonce: str
    client_id: str
