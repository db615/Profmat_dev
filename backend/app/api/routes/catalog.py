"""Catalog data - public endpoints."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from app.api.dependencies import DatabaseDep
from app.models import (
    Country,
    CourseProgram,
    Funding,
    News,
    Professor,
    University,
    UniversityAdvertisement,
    VisaInformation,
)

router = APIRouter(prefix="/api/v1", tags=["Catalog"])


class Payload(BaseModel):
    model_config = ConfigDict(extra="forbid")


def list_countries(session: DatabaseDep):
    return list(session.scalars(select(Country)))


def list_visas(country_code: str, session: DatabaseDep):
    return list(session.scalars(select(VisaInformation).where(VisaInformation.country_code == country_code)))


def list_universities(session: DatabaseDep, country_code: str | None = None):
    stmt = select(University)
    if country_code:
        stmt = stmt.where(University.country_code == country_code)
    return list(session.scalars(stmt))


def university_detail(university_id: UUID, session: DatabaseDep):
    university = session.get(University, university_id)
    if university is None:
        raise HTTPException(status_code=404, detail="University not found")
    return university


def list_programs(university_id: UUID, session: DatabaseDep):
    return list(session.scalars(select(CourseProgram).where(CourseProgram.university_id == university_id)))


def list_professors(university_id: UUID, session: DatabaseDep, department_id: UUID | None = None):
    stmt = select(Professor).where(Professor.university_id == university_id)
    if department_id:
        stmt = stmt.where(Professor.department_id == department_id)
    return list(session.scalars(stmt))


def list_funding(university_id: UUID, session: DatabaseDep):
    return list(session.scalars(select(Funding).where(Funding.university_id == university_id)))


def list_news(session: DatabaseDep, limit: int = Query(default=20, ge=1, le=100)):
    stmt = select(News).order_by(News.published_at.desc())
    return list(session.scalars(stmt.limit(limit)))


def list_advertisements(session: DatabaseDep, university_id: UUID | None = None):
    stmt = select(UniversityAdvertisement)
    if university_id:
        stmt = stmt.where(UniversityAdvertisement.university_id == university_id)
    return list(session.scalars(stmt))


router.add_api_route("/countries", list_countries, methods=["GET"])
router.add_api_route("/countries/{country_code}/visas", list_visas, methods=["GET"])
router.add_api_route("/universities", list_universities, methods=["GET"])
router.add_api_route("/universities/{university_id}", university_detail, methods=["GET"])
router.add_api_route("/universities/{university_id}/programs", list_programs, methods=["GET"])
router.add_api_route("/universities/{university_id}/professors", list_professors, methods=["GET"])
router.add_api_route("/universities/{university_id}/funding", list_funding, methods=["GET"])
router.add_api_route("/news", list_news, methods=["GET"])
router.add_api_route("/advertisements", list_advertisements, methods=["GET"])
