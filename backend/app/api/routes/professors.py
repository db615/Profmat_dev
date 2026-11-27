"""Public professors directory: search, filters, detail and related data."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, or_, select

from app.api.dependencies import DatabaseDep
from app.models import (
    Country,
    CourseProgram,
    Department,
    Funding,
    Professor,
    University,
)
from app.schemas.profmat import (
    CourseProgramRead,
    DepartmentRead,
    FundingRead,
    ProfessorDetailRead,
    ProfessorFiltersRead,
    ProfessorOpportunitiesRead,
    ProfessorPage,
    ProfessorRead,
    PublicationRead,
    SuggestionRead,
    UniversityRead,
)

router = APIRouter(tags=["Professors"])

SORT_COLUMNS = {
    "name": Professor.name,
    "designation": Professor.designation,
    "university": University.name,
    "department": Department.name,
}


def _require_professor(session, professor_id: UUID) -> Professor:
    professor = session.get(Professor, professor_id)
    if professor is None:
        raise HTTPException(status_code=404, detail="Professor not found")
    return professor


def _detail(session, professor: Professor) -> ProfessorDetailRead:
    university = session.get(University, professor.university_id)
    department = (
        session.get(Department, professor.department_id) if professor.department_id else None
    )
    return ProfessorDetailRead(
        **ProfessorRead.model_validate(professor).model_dump(),
        university=UniversityRead.model_validate(university),
        department=DepartmentRead.model_validate(department) if department else None,
    )


def list_professors(
    session: DatabaseDep,
    q: str | None = Query(default=None, max_length=200),
    university_id: UUID | None = None,
    department_id: UUID | None = None,
    country_code: str | None = None,
    sort: str = Query(default="name", max_length=40),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ProfessorPage:
    stmt = (
        select(Professor)
        .join(University, Professor.university_id == University.id)
        .outerjoin(Department, Professor.department_id == Department.id)
    )
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Professor.name.ilike(pattern),
                Professor.research_areas.ilike(pattern),
                Professor.email.ilike(pattern),
                University.name.ilike(pattern),
                Department.name.ilike(pattern),
            )
        )
    if university_id:
        stmt = stmt.where(Professor.university_id == university_id)
    if department_id:
        stmt = stmt.where(Professor.department_id == department_id)
    if country_code:
        stmt = stmt.where(University.country_code == country_code)

    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    descending = sort.startswith("-")
    column = SORT_COLUMNS.get(sort.lstrip("-"), Professor.name)
    ordering = column.desc() if descending else column.asc()
    rows = list(
        session.scalars(stmt.order_by(ordering, Professor.name).offset(offset).limit(limit))
    )

    university_ids = {professor.university_id for professor in rows}
    department_ids = {professor.department_id for professor in rows if professor.department_id}
    universities = (
        {
            university.id: university
            for university in session.scalars(
                select(University).where(University.id.in_(university_ids))
            )
        }
        if university_ids
        else {}
    )
    departments = (
        {
            department.id: department
            for department in session.scalars(
                select(Department).where(Department.id.in_(department_ids))
            )
        }
        if department_ids
        else {}
    )

    items = [
        ProfessorDetailRead(
            **ProfessorRead.model_validate(professor).model_dump(),
            university=UniversityRead.model_validate(universities[professor.university_id]),
            department=(
                DepartmentRead.model_validate(departments[professor.department_id])
                if professor.department_id
                else None
            ),
        )
        for professor in rows
    ]
    return ProfessorPage(items=items, total=total, limit=limit, offset=offset)


def professor_filters(session: DatabaseDep) -> ProfessorFiltersRead:
    return ProfessorFiltersRead(
        countries=list(session.scalars(select(Country).order_by(Country.name))),
        universities=list(session.scalars(select(University).order_by(University.name))),
        departments=list(session.scalars(select(Department).order_by(Department.name))),
    )


def search_suggestions(
    session: DatabaseDep,
    q: str = Query(min_length=1, max_length=100),
    limit: int = Query(default=8, ge=1, le=20),
) -> list[SuggestionRead]:
    pattern = f"%{q.strip()}%"
    suggestions: list[SuggestionRead] = []
    for professor in session.scalars(
        select(Professor).where(Professor.name.ilike(pattern)).order_by(Professor.name).limit(limit)
    ):
        suggestions.append(
            SuggestionRead(
                type="professor",
                id=professor.id,
                label=professor.name,
                subtitle=professor.designation,
            )
        )
    for university in session.scalars(
        select(University)
        .where(University.name.ilike(pattern))
        .order_by(University.name)
        .limit(limit)
    ):
        suggestions.append(
            SuggestionRead(
                type="university",
                id=university.id,
                label=university.name,
                subtitle=university.country_code,
            )
        )
    for department in session.scalars(
        select(Department)
        .where(Department.name.ilike(pattern))
        .order_by(Department.name)
        .limit(limit)
    ):
        suggestions.append(
            SuggestionRead(type="department", id=department.id, label=department.name)
        )
    return suggestions


def professor_detail(professor_id: UUID, session: DatabaseDep) -> ProfessorDetailRead:
    return _detail(session, _require_professor(session, professor_id))


def professor_research_interests(professor_id: UUID, session: DatabaseDep) -> list[str]:
    professor = _require_professor(session, professor_id)
    text = (professor.research_areas or "").replace(";", ",")
    return [part.strip() for part in text.split(",") if part.strip()]


def professor_publications(professor_id: UUID, session: DatabaseDep) -> list[PublicationRead]:
    _require_professor(session, professor_id)
    return []


def professor_opportunities(professor_id: UUID, session: DatabaseDep) -> ProfessorOpportunitiesRead:
    professor = _require_professor(session, professor_id)
    funding = list(
        session.scalars(
            select(Funding)
            .where(Funding.university_id == professor.university_id)
            .order_by(Funding.deadline, Funding.title)
        )
    )
    programs = list(
        session.scalars(
            select(CourseProgram)
            .where(CourseProgram.university_id == professor.university_id)
            .order_by(CourseProgram.name)
        )
    )
    return ProfessorOpportunitiesRead(
        funding=[FundingRead.model_validate(item) for item in funding],
        programs=[CourseProgramRead.model_validate(item) for item in programs],
    )


def related_professors(
    professor_id: UUID,
    session: DatabaseDep,
    limit: int = Query(default=10, ge=1, le=50),
) -> list[ProfessorRead]:
    professor = _require_professor(session, professor_id)
    stmt = select(Professor).where(Professor.id != professor.id)
    if professor.department_id:
        stmt = stmt.where(Professor.department_id == professor.department_id)
    else:
        stmt = stmt.where(Professor.university_id == professor.university_id)
    return list(session.scalars(stmt.order_by(Professor.name).limit(limit)))


router.add_api_route("/professors", list_professors, methods=["GET"], response_model=ProfessorPage)
router.add_api_route(
    "/professors/filters",
    professor_filters,
    methods=["GET"],
    response_model=ProfessorFiltersRead,
)
router.add_api_route(
    "/professors/search-suggestions",
    search_suggestions,
    methods=["GET"],
    response_model=list[SuggestionRead],
)
router.add_api_route(
    "/professors/{professor_id}",
    professor_detail,
    methods=["GET"],
    response_model=ProfessorDetailRead,
)
router.add_api_route(
    "/professors/{professor_id}/research-interests",
    professor_research_interests,
    methods=["GET"],
    response_model=list[str],
)
router.add_api_route(
    "/professors/{professor_id}/publications",
    professor_publications,
    methods=["GET"],
    response_model=list[PublicationRead],
)
router.add_api_route(
    "/professors/{professor_id}/opportunities",
    professor_opportunities,
    methods=["GET"],
    response_model=ProfessorOpportunitiesRead,
)
router.add_api_route(
    "/professors/{professor_id}/related-professors",
    related_professors,
    methods=["GET"],
    response_model=list[ProfessorRead],
)
