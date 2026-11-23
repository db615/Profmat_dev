"""University applications."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.api.dependencies import DatabaseDep, UserDep
from app.core.database import utcnow
from app.api.routes.common import commit, get_owned
from app.models import ApplicationDocument, CourseProgram, UniversityApplication, UniversityApplicationStageHistory

router = APIRouter(prefix="/api/v1", tags=["Applications"])


class Payload(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ApplicationInput(Payload):
    university_id: UUID
    course_program_id: UUID
    application_type: str | None = Field(default=None, max_length=100)
    stage: str = Field(default="SAVED", max_length=100)
    deadline: str | None = None
    application_reference: str | None = Field(default=None, max_length=200)


class StageInput(Payload):
    stage: str = Field(max_length=100)
    notes: str | None = None


class DocumentInput(Payload):
    document_type: str = Field(max_length=100)
    file_url: str | None = Field(default=None, max_length=1000)
    status: str = Field(default="UPLOADED", max_length=50)


def list_applications(user: UserDep, session: DatabaseDep):
    return list(session.scalars(select(UniversityApplication).where(UniversityApplication.user_id == user.id)))


def create_application(data: ApplicationInput, user: UserDep, session: DatabaseDep):
    program = session.get(CourseProgram, data.course_program_id)
    if program is None or program.university_id != data.university_id:
        raise HTTPException(status_code=422, detail="Program must belong to the selected university")
    payload = data.model_dump()
    if payload.get("deadline") and isinstance(payload["deadline"], str):
        from datetime import date as _date

        try:
            payload["deadline"] = _date.fromisoformat(payload["deadline"])
        except Exception:
            payload["deadline"] = None
    return commit(session, UniversityApplication(user_id=user.id, **payload))


def update_application_stage(application_id: UUID, data: StageInput, user: UserDep, session: DatabaseDep):
    application = get_owned(session, UniversityApplication, application_id, user.id)
    old = application.stage
    application.stage = data.stage
    if data.stage.upper() == "SUBMITTED" and application.submitted_at is None:
        application.submitted_at = utcnow()
    session.add(UniversityApplicationStageHistory(application_id=application.id, previous_stage=old, new_stage=data.stage, notes=data.notes))
    return commit(session, application)


def add_document(application_id: UUID, data: DocumentInput, user: UserDep, session: DatabaseDep):
    get_owned(session, UniversityApplication, application_id, user.id)
    return commit(session, ApplicationDocument(university_application_id=application_id, **data.model_dump()))


router.add_api_route("/applications", list_applications, methods=["GET"])
router.add_api_route("/applications", create_application, methods=["POST"], status_code=status.HTTP_201_CREATED)
router.add_api_route("/applications/{application_id}/stage", update_application_stage, methods=["PATCH"])
router.add_api_route("/applications/{application_id}/documents", add_document, methods=["POST"], status_code=status.HTTP_201_CREATED)
