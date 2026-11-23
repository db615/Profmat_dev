"""Professor outreach."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.api.dependencies import DatabaseDep, UserDep
from app.core.database import utcnow
from app.api.routes.common import commit, get_owned
from app.models import EmailRecord, Professor, ProfessorOutreach, ProfessorOutreachStageHistory

router = APIRouter(prefix="/api/v1", tags=["Outreach"])


class Payload(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OutreachInput(Payload):
    professor_id: UUID
    funding_id: UUID | None = None
    purpose: str = Field(max_length=2000)
    stage: str = Field(default="RESEARCHING", max_length=100)
    planned_send_at: str | None = None
    response_status: str = Field(default="PENDING", max_length=50)
    outcome: str | None = Field(default=None, max_length=100)


class StageInput(Payload):
    stage: str = Field(max_length=100)
    notes: str | None = None


class EmailInput(Payload):
    subject: str | None = Field(default=None, max_length=500)
    body: str | None = None
    direction: str = Field(max_length=20)
    response_summary: str | None = None


def list_outreach(user: UserDep, session: DatabaseDep):
    return list(session.scalars(select(ProfessorOutreach).where(ProfessorOutreach.user_id == user.id)))


def create_outreach(data: OutreachInput, user: UserDep, session: DatabaseDep):
    if session.get(Professor, data.professor_id) is None:
        raise HTTPException(status_code=404, detail="Professor not found")
    payload = data.model_dump()
    for key in ["planned_send_at"]:
        if payload.get(key) and isinstance(payload[key], str):
            from datetime import datetime as _dt
            try:
                payload[key] = _dt.fromisoformat(payload[key])
            except Exception:
                payload[key] = None
    return commit(session, ProfessorOutreach(user_id=user.id, **payload))


def update_outreach_stage(outreach_id: UUID, data: StageInput, user: UserDep, session: DatabaseDep):
    outreach = get_owned(session, ProfessorOutreach, outreach_id, user.id)
    old = outreach.stage
    outreach.stage = data.stage
    session.add(ProfessorOutreachStageHistory(outreach_id=outreach.id, previous_stage=old, new_stage=data.stage, notes=data.notes))
    return commit(session, outreach)


def add_email(outreach_id: UUID, data: EmailInput, user: UserDep, session: DatabaseDep):
    get_owned(session, ProfessorOutreach, outreach_id, user.id)
    email = EmailRecord(outreach_id=outreach_id, **data.model_dump())
    if data.direction == "OUTBOUND":
        email.sent_at = utcnow()
    return commit(session, email)


router.add_api_route("/outreach", list_outreach, methods=["GET"])
router.add_api_route("/outreach", create_outreach, methods=["POST"], status_code=status.HTTP_201_CREATED)
router.add_api_route("/outreach/{outreach_id}/stage", update_outreach_stage, methods=["PATCH"])
router.add_api_route("/outreach/{outreach_id}/emails", add_email, methods=["POST"], status_code=status.HTTP_201_CREATED)
