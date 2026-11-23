"""User profile and preferences."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.api.dependencies import DatabaseDep, UserDep
from app.core.database import utcnow
from app.api.routes.common import commit, get_owned
from app.models import AcademicProfile, CountryPreference, CV, ResearchProfile

router = APIRouter(prefix="/api/v1", tags=["Profile"])


class Payload(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AcademicProfileInput(Payload):
    degree_level: str | None = None
    field_of_study: str | None = None
    previous_university: str | None = None
    gpa: str | None = None
    graduation_year: int | None = Field(default=None, ge=1900, le=2100)
    english_test_score: str | None = None


class ResearchProfileInput(Payload):
    research_interests: str | None = None
    publications: str | None = None
    skills: str | None = None
    research_experience: str | None = None
    preferred_degree: str | None = None


class CVInput(Payload):
    file_url: str = Field(min_length=1, max_length=1000)
    version: str | None = Field(default=None, max_length=50)


class PreferenceInput(Payload):
    country_code: str = Field(min_length=2, max_length=10)
    priority: int | None = Field(default=None, ge=1, le=100)


def read_academic_profile(user: UserDep, session: DatabaseDep):
    profile = session.scalars(select(AcademicProfile).where(AcademicProfile.user_id == user.id)).first()
    return profile


def save_academic_profile(data: AcademicProfileInput, user: UserDep, session: DatabaseDep):
    profile = session.scalars(select(AcademicProfile).where(AcademicProfile.user_id == user.id)).first()
    if profile is None:
        profile = AcademicProfile(user_id=user.id, **data.model_dump())
    else:
        for key, value in data.model_dump().items():
            setattr(profile, key, value)
    return commit(session, profile)


def read_research_profile(user: UserDep, session: DatabaseDep):
    profile = session.scalars(select(ResearchProfile).where(ResearchProfile.user_id == user.id)).first()
    return profile


def save_research_profile(data: ResearchProfileInput, user: UserDep, session: DatabaseDep):
    profile = session.scalars(select(ResearchProfile).where(ResearchProfile.user_id == user.id)).first()
    if profile is None:
        profile = ResearchProfile(user_id=user.id, **data.model_dump())
    else:
        for key, value in data.model_dump().items():
            setattr(profile, key, value)
    return commit(session, profile)


def list_cvs(user: UserDep, session: DatabaseDep):
    return list(session.scalars(select(CV).where(CV.user_id == user.id)))


def add_cv(data: CVInput, user: UserDep, session: DatabaseDep):
    return commit(session, CV(user_id=user.id, uploaded_at=utcnow(), **data.model_dump()))


def list_preferences(user: UserDep, session: DatabaseDep):
    return list(session.scalars(select(CountryPreference).where(CountryPreference.user_id == user.id)))


def add_preference(data: PreferenceInput, user: UserDep, session: DatabaseDep):
    return commit(session, CountryPreference(user_id=user.id, **data.model_dump()))


def delete_preference(preference_id: UUID, user: UserDep, session: DatabaseDep):
    preference = session.get(CountryPreference, preference_id)
    if preference is None or preference.user_id != user.id:
        raise HTTPException(status_code=404, detail="Preference not found")
    session.delete(preference)
    session.commit()
    return {"status": "deleted"}


router.add_api_route("/me/academic-profile", read_academic_profile, methods=["GET"])
router.add_api_route("/me/academic-profile", save_academic_profile, methods=["PUT"])
router.add_api_route("/me/research-profile", read_research_profile, methods=["GET"])
router.add_api_route("/me/research-profile", save_research_profile, methods=["PUT"])
router.add_api_route("/me/cvs", list_cvs, methods=["GET"])
router.add_api_route("/me/cvs", add_cv, methods=["POST"], status_code=status.HTTP_201_CREATED)
router.add_api_route("/me/preferences", list_preferences, methods=["GET"])
router.add_api_route("/me/preferences", add_preference, methods=["POST"], status_code=status.HTTP_201_CREATED)
router.add_api_route("/me/preferences/{preference_id}", delete_preference, methods=["DELETE"])
