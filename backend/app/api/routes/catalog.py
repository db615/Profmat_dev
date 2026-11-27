"""Catalog data - public endpoints."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.api.dependencies import DatabaseDep
from app.models import (
    Country,
    CourseProgram,
    Department,
    Funding,
    News,
    Professor,
    University,
    UniversityAdvertisement,
    VisaInformation,
)
from app.schemas.profmat import (
    CountryRead,
    CourseProgramRead,
    DepartmentRead,
    FundingRead,
    NewsRead,
    ProfessorRead,
    UniversityAdvertisementRead,
    UniversityRead,
    VisaInformationRead,
)

router = APIRouter(tags=["Catalog"])


def list_countries(session: DatabaseDep) -> list[CountryRead]:
    return list(session.scalars(select(Country)))


def list_visas(country_code: str, session: DatabaseDep) -> list[VisaInformationRead]:
    return list(
        session.scalars(select(VisaInformation).where(VisaInformation.country_code == country_code))
    )


def list_universities(
    session: DatabaseDep,
    country_code: str | None = None,
    q: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[UniversityRead]:
    stmt = select(University)
    if country_code:
        stmt = stmt.where(University.country_code == country_code)
    if q:
        stmt = stmt.where(University.name.ilike(f"%{q.strip()}%"))
    return list(session.scalars(stmt.order_by(University.name).offset(offset).limit(limit)))


def university_detail(university_id: UUID, session: DatabaseDep) -> UniversityRead:
    university = session.get(University, university_id)
    if university is None:
        raise HTTPException(status_code=404, detail="University not found")
    return university


def list_departments(university_id: UUID, session: DatabaseDep) -> list[DepartmentRead]:
    if session.get(University, university_id) is None:
        raise HTTPException(status_code=404, detail="University not found")
    return list(
        session.scalars(
            select(Department)
            .where(Department.university_id == university_id)
            .order_by(Department.name)
        )
    )


def list_programs(university_id: UUID, session: DatabaseDep) -> list[CourseProgramRead]:
    return list(
        session.scalars(
            select(CourseProgram)
            .where(CourseProgram.university_id == university_id)
            .order_by(CourseProgram.name)
        )
    )


def list_professors(
    university_id: UUID, session: DatabaseDep, department_id: UUID | None = None
) -> list[ProfessorRead]:
    stmt = select(Professor).where(Professor.university_id == university_id)
    if department_id:
        stmt = stmt.where(Professor.department_id == department_id)
    return list(session.scalars(stmt.order_by(Professor.name)))


def list_funding(university_id: UUID, session: DatabaseDep) -> list[FundingRead]:
    return list(session.scalars(select(Funding).where(Funding.university_id == university_id)))


def list_news(session: DatabaseDep, limit: int = Query(default=20, ge=1, le=100)) -> list[NewsRead]:
    stmt = select(News).order_by(News.published_at.desc()).limit(limit)
    return list(session.scalars(stmt))


def list_advertisements(
    session: DatabaseDep, university_id: UUID | None = None
) -> list[UniversityAdvertisementRead]:
    stmt = select(UniversityAdvertisement)
    if university_id:
        stmt = stmt.where(UniversityAdvertisement.university_id == university_id)
    return list(session.scalars(stmt.order_by(UniversityAdvertisement.title)))


router.add_api_route(
    "/countries", list_countries, methods=["GET"], response_model=list[CountryRead]
)
router.add_api_route(
    "/countries/{country_code}/visas",
    list_visas,
    methods=["GET"],
    response_model=list[VisaInformationRead],
)
router.add_api_route(
    "/universities",
    list_universities,
    methods=["GET"],
    response_model=list[UniversityRead],
)
router.add_api_route(
    "/universities/{university_id}",
    university_detail,
    methods=["GET"],
    response_model=UniversityRead,
)
router.add_api_route(
    "/universities/{university_id}/programs",
    list_programs,
    methods=["GET"],
    response_model=list[CourseProgramRead],
)
router.add_api_route(
    "/universities/{university_id}/departments",
    list_departments,
    methods=["GET"],
    response_model=list[DepartmentRead],
)
router.add_api_route(
    "/universities/{university_id}/professors",
    list_professors,
    methods=["GET"],
    response_model=list[ProfessorRead],
)
router.add_api_route(
    "/universities/{university_id}/funding",
    list_funding,
    methods=["GET"],
    response_model=list[FundingRead],
)
router.add_api_route("/news", list_news, methods=["GET"], response_model=list[NewsRead])
router.add_api_route(
    "/advertisements",
    list_advertisements,
    methods=["GET"],
    response_model=list[UniversityAdvertisementRead],
)
