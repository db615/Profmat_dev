"""User profile and preferences."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select

from app.api.dependencies import DatabaseDep, UserDep
from app.api.routes.common import commit
from app.core.database import utcnow
from app.models import CV, AcademicProfile, CountryPreference, ResearchProfile
from app.schemas.profmat import (
    AcademicProfileRead,
    CountryPreferenceRead,
    CVRead,
    ProfileCompletenessRead,
    ResearchProfileRead,
)

router = APIRouter(tags=["Profile"])


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


def read_academic_profile(user: UserDep, session: DatabaseDep) -> AcademicProfileRead | None:
    return session.scalars(
        select(AcademicProfile).where(AcademicProfile.user_id == user.id)
    ).first()


def save_academic_profile(
    data: AcademicProfileInput, user: UserDep, session: DatabaseDep
) -> AcademicProfileRead:
    profile = session.scalars(
        select(AcademicProfile).where(AcademicProfile.user_id == user.id)
    ).first()
    if profile is None:
        profile = AcademicProfile(user_id=user.id, **data.model_dump())
    else:
        for key, value in data.model_dump().items():
            setattr(profile, key, value)
    return commit(session, profile)


def read_research_profile(user: UserDep, session: DatabaseDep) -> ResearchProfileRead | None:
    return session.scalars(
        select(ResearchProfile).where(ResearchProfile.user_id == user.id)
    ).first()


def save_research_profile(
    data: ResearchProfileInput, user: UserDep, session: DatabaseDep
) -> ResearchProfileRead:
    profile = session.scalars(
        select(ResearchProfile).where(ResearchProfile.user_id == user.id)
    ).first()
    if profile is None:
        profile = ResearchProfile(user_id=user.id, **data.model_dump())
    else:
        for key, value in data.model_dump().items():
            setattr(profile, key, value)
    return commit(session, profile)


def list_cvs(user: UserDep, session: DatabaseDep) -> list[CVRead]:
    return list(session.scalars(select(CV).where(CV.user_id == user.id)))


def add_cv(data: CVInput, user: UserDep, session: DatabaseDep) -> CVRead:
    return commit(session, CV(user_id=user.id, uploaded_at=utcnow(), **data.model_dump()))


def list_preferences(user: UserDep, session: DatabaseDep) -> list[CountryPreferenceRead]:
    return list(
        session.scalars(select(CountryPreference).where(CountryPreference.user_id == user.id))
    )


def add_preference(
    data: PreferenceInput, user: UserDep, session: DatabaseDep
) -> CountryPreferenceRead:
    return commit(session, CountryPreference(user_id=user.id, **data.model_dump()))


def delete_preference(preference_id: UUID, user: UserDep, session: DatabaseDep) -> dict[str, str]:
    preference = session.get(CountryPreference, preference_id)
    if preference is None or preference.user_id != user.id:
        raise HTTPException(status_code=404, detail="Preference not found")
    session.delete(preference)
    session.commit()
    return {"status": "deleted"}


def profile_completeness(user: UserDep, session: DatabaseDep) -> ProfileCompletenessRead:
    academic = session.scalars(
        select(AcademicProfile).where(AcademicProfile.user_id == user.id)
    ).first()
    research = session.scalars(
        select(ResearchProfile).where(ResearchProfile.user_id == user.id)
    ).first()
    cv_count = (
        session.scalar(select(func.count()).select_from(CV).where(CV.user_id == user.id)) or 0
    )
    preference_count = (
        session.scalar(
            select(func.count())
            .select_from(CountryPreference)
            .where(CountryPreference.user_id == user.id)
        )
        or 0
    )
    checks = [
        (
            "academic_profile",
            academic is not None
            and bool(academic.degree_level)
            and bool(academic.field_of_study)
            and academic.graduation_year is not None,
        ),
        ("research_profile", research is not None and bool(research.research_interests)),
        ("skills", research is not None and bool(research.skills)),
        ("publications", research is not None and bool(research.publications)),
        ("cv", cv_count > 0),
        ("country_preferences", preference_count > 0),
    ]
    completed = [name for name, done in checks if done]
    missing = [name for name, done in checks if not done]
    percentage = round(100 * len(completed) / len(checks))
    return ProfileCompletenessRead(
        percentage=percentage,
        completed=completed,
        missing=missing,
    )


router.add_api_route(
    "/me/academic-profile",
    read_academic_profile,
    methods=["GET"],
    response_model=AcademicProfileRead | None,
)
router.add_api_route(
    "/me/academic-profile",
    save_academic_profile,
    methods=["PUT"],
    response_model=AcademicProfileRead,
)
router.add_api_route(
    "/me/research-profile",
    read_research_profile,
    methods=["GET"],
    response_model=ResearchProfileRead | None,
)
router.add_api_route(
    "/me/research-profile",
    save_research_profile,
    methods=["PUT"],
    response_model=ResearchProfileRead,
)
router.add_api_route("/me/cvs", list_cvs, methods=["GET"], response_model=list[CVRead])
router.add_api_route(
    "/me/cvs",
    add_cv,
    methods=["POST"],
    status_code=status.HTTP_201_CREATED,
    response_model=CVRead,
)
router.add_api_route(
    "/me/preferences",
    list_preferences,
    methods=["GET"],
    response_model=list[CountryPreferenceRead],
)
router.add_api_route(
    "/me/preferences",
    add_preference,
    methods=["POST"],
    status_code=status.HTTP_201_CREATED,
    response_model=CountryPreferenceRead,
)
router.add_api_route(
    "/me/preferences/{preference_id}",
    delete_preference,
    methods=["DELETE"],
    response_model=dict[str, str],
)
router.add_api_route(
    "/me/completeness",
    profile_completeness,
    methods=["GET"],
    response_model=ProfileCompletenessRead,
)
