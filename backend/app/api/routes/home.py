"""Home dashboard aggregates."""

from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.dependencies import DatabaseDep
from app.models import (
    Country,
    CourseProgram,
    Funding,
    News,
    Professor,
    University,
    UniversityAdvertisement,
)
from app.schemas.profmat import HomeRead, HomeSummaryRead

router = APIRouter(tags=["Home"])


def home(session: DatabaseDep) -> HomeRead:
    news = list(session.scalars(select(News).order_by(News.published_at.desc()).limit(5)))
    advertisements = list(
        session.scalars(
            select(UniversityAdvertisement).order_by(UniversityAdvertisement.title).limit(5)
        )
    )
    featured_funding = list(
        session.scalars(
            select(Funding)
            .where(Funding.deadline.is_not(None))
            .order_by(Funding.deadline, Funding.title)
            .limit(5)
        )
    )
    return HomeRead(
        news=news,
        advertisements=advertisements,
        featured_funding=featured_funding,
    )


def home_summary(session: DatabaseDep) -> HomeSummaryRead:
    def count(model) -> int:
        return session.scalar(select(func.count()).select_from(model)) or 0

    return HomeSummaryRead(
        countries=count(Country),
        universities=count(University),
        professors=count(Professor),
        programs=count(CourseProgram),
        funding=count(Funding),
        news=count(News),
    )


router.add_api_route("/home", home, methods=["GET"], response_model=HomeRead)
router.add_api_route("/home/summary", home_summary, methods=["GET"], response_model=HomeSummaryRead)
