from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import select

from search_prof.backend.app.api.dependencies import AdminDep, DatabaseDep
from search_prof.backend.app.models import User
from search_prof.backend.app.schemas import UserRead

router = APIRouter(prefix="/api/v1/admin", tags=["Authorization"])


@router.get("/users", response_model=list[UserRead])
def list_users(
    admin: AdminDep,
    session: DatabaseDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[UserRead]:
    users = session.scalars(
        select(User).order_by(User.created_at, User.id).limit(limit).offset(offset)
    )
    return [UserRead.model_validate(user) for user in users]
