"""Checklists."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.api.dependencies import DatabaseDep, UserDep
from app.api.routes.common import commit, get_owned
from app.core.database import utcnow
from app.models import Checklist, ChecklistItem, ProfessorOutreach, UniversityApplication
from app.schemas.profmat import ChecklistItemRead, ChecklistRead

router = APIRouter(tags=["Checklists"])


class Payload(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ChecklistInput(Payload):
    professor_outreach_id: UUID | None = None
    university_application_id: UUID | None = None
    title: str = Field(max_length=300)
    checklist_type: str = Field(max_length=100)
    status: str = Field(default="OPEN", max_length=50)


class ChecklistItemInput(Payload):
    title: str = Field(max_length=300)
    description: str | None = None
    due_date: str | None = None
    notes: str | None = None


def list_checklists(user: UserDep, session: DatabaseDep) -> list[ChecklistRead]:
    return list(session.scalars(select(Checklist).where(Checklist.user_id == user.id)))


def create_checklist(data: ChecklistInput, user: UserDep, session: DatabaseDep) -> ChecklistRead:
    if data.university_application_id:
        get_owned(session, UniversityApplication, data.university_application_id, user.id)
    if data.professor_outreach_id:
        get_owned(session, ProfessorOutreach, data.professor_outreach_id, user.id)
    return commit(session, Checklist(user_id=user.id, **data.model_dump()))


def add_checklist_item(
    checklist_id: UUID, data: ChecklistItemInput, user: UserDep, session: DatabaseDep
) -> ChecklistItemRead:
    get_owned(session, Checklist, checklist_id, user.id)
    payload = data.model_dump()
    if payload.get("due_date") and isinstance(payload["due_date"], str):
        from datetime import date as _date

        try:
            payload["due_date"] = _date.fromisoformat(payload["due_date"])
        except ValueError:
            payload["due_date"] = None
    return commit(session, ChecklistItem(checklist_id=checklist_id, status="TODO", **payload))


def complete_checklist_item(
    checklist_id: UUID, item_id: UUID, user: UserDep, session: DatabaseDep
) -> ChecklistItemRead:
    get_owned(session, Checklist, checklist_id, user.id)
    item = session.get(ChecklistItem, item_id)
    if item is None or item.checklist_id != checklist_id:
        raise HTTPException(status_code=404, detail="Checklist item not found")
    item.status, item.completed_at = "COMPLETED", utcnow()
    return commit(session, item)


router.add_api_route(
    "/checklists", list_checklists, methods=["GET"], response_model=list[ChecklistRead]
)
router.add_api_route(
    "/checklists",
    create_checklist,
    methods=["POST"],
    status_code=status.HTTP_201_CREATED,
    response_model=ChecklistRead,
)
router.add_api_route(
    "/checklists/{checklist_id}/items",
    add_checklist_item,
    methods=["POST"],
    status_code=status.HTTP_201_CREATED,
    response_model=ChecklistItemRead,
)
router.add_api_route(
    "/checklists/{checklist_id}/items/{item_id}/complete",
    complete_checklist_item,
    methods=["PATCH"],
    response_model=ChecklistItemRead,
)
