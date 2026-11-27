"""Idempotent ETL from the crawler's raw tables into the normalized Profmat catalog.

The crawler (`professor_search`, branch `ps/feat/llm_filter`) owns the raw tables
``university``, ``department``, ``professors``, ``personal_info`` and
``program_details``. This module reads them through a separate source engine and
upserts the normalized tables the API serves (``universities``, ``departments``,
``professors``, ``course_programs``).

The raw schema has no country column, so the caller supplies a default country
that must already exist in ``countries`` (the demo seed creates the usual set).
Raw columns with no normalized target (for example publications, awards,
tuition and scholarships) are intentionally skipped; see PROJECT_NOTES.md.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import MetaData, Table, func, inspect, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.models import Country, CourseProgram, Department, Professor, University

CRAWLER_TABLES = (
    "university",
    "department",
    "professors",
    "personal_info",
    "program_details",
)

_DATE_FORMATS = (
    "%Y-%m-%d",
    "%d %B %Y",
    "%B %d, %Y",
    "%d %b %Y",
    "%b %d, %Y",
    "%d/%m/%Y",
    "%m/%d/%Y",
)


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_date(value: Any) -> date | None:
    text = _clean(value)
    if text is None:
        return None
    for date_format in _DATE_FORMATS:
        try:
            return datetime.strptime(text, date_format).date()
        except ValueError:
            continue
    return None


def _merge_terms(existing: str | None, incoming: str | None) -> tuple[str | None, int]:
    incoming = _clean(incoming)
    if incoming is None:
        return existing, 0
    current = [part.strip() for part in (existing or "").split(",") if part.strip()]
    seen = {part.casefold() for part in current}
    added = 0
    for part in (item.strip() for item in incoming.split(",")):
        if part and part.casefold() not in seen:
            current.append(part)
            seen.add(part.casefold())
            added += 1
    return (", ".join(current) if current else existing), added


def _reflect(source_engine: Engine) -> dict[str, Table]:
    available = set(inspect(source_engine).get_table_names())
    names = [name for name in CRAWLER_TABLES if name in available]
    if not names:
        return {}
    metadata = MetaData()
    metadata.reflect(bind=source_engine, only=names)
    return {name: metadata.tables[name] for name in names}


def _rows(source_engine: Engine, table: Table) -> list[dict[str, Any]]:
    with source_engine.connect() as connection:
        return [dict(row._mapping) for row in connection.execute(select(table))]


def _initial_counts() -> dict[str, int]:
    return {
        "universities": 0,
        "departments": 0,
        "professors": 0,
        "programs": 0,
        "personal_info_matched": 0,
        "personal_info_added": 0,
        "created_universities": 0,
        "created_departments": 0,
        "created_professors": 0,
        "created_programs": 0,
    }


def sync_crawler(
    session: Session,
    source_engine: Engine,
    default_country_code: str = "US",
    *,
    dry_run: bool = False,
) -> dict[str, int]:
    """Upsert raw crawler rows into the normalized catalog.

    Returns processed-row counts plus ``created_*`` counters. Processed counts are
    stable across runs; ``created_*`` is zero once data is in place. Raises
    ``ValueError`` when the default country is not seeded, so FK integrity is never
    silently broken.
    """

    if session.get(Country, default_country_code) is None:
        raise ValueError(
            f"Country {default_country_code!r} is not seeded; run `python -m app.manage seed` "
            "or pass --default-country with an existing code"
        )

    tables = _reflect(source_engine)
    counts = _initial_counts()
    universities: dict[str, University] = {}
    departments: dict[tuple[Any, str], Department] = {}

    def university_for(name: Any, website: str | None = None) -> University | None:
        cleaned = _clean(name)
        if cleaned is None:
            return None
        key = cleaned.casefold()
        cached = universities.get(key)
        if cached is not None:
            if website and not cached.website:
                cached.website = website
            return cached
        found = session.scalars(
            select(University).where(
                func.lower(University.name) == key,
                University.country_code == default_country_code,
            )
        ).first()
        if found is None:
            found = University(name=cleaned, country_code=default_country_code)
            session.add(found)
            session.flush()
            counts["created_universities"] += 1
        if website and not found.website:
            found.website = website
        universities[key] = found
        counts["universities"] += 1
        return found

    def department_for(
        university: University, name: Any, description: str | None = None
    ) -> Department:
        cleaned = _clean(name) or "General"
        key = (university.id, cleaned.casefold())
        cached = departments.get(key)
        if cached is not None:
            if description and not cached.description:
                cached.description = description
            return cached
        found = session.scalars(
            select(Department).where(
                Department.university_id == university.id,
                func.lower(Department.name) == cleaned.casefold(),
            )
        ).first()
        if found is None:
            found = Department(university_id=university.id, name=cleaned)
            session.add(found)
            session.flush()
            counts["created_departments"] += 1
        if description and not found.description:
            found.description = description
        departments[key] = found
        counts["departments"] += 1
        return found

    if "university" in tables:
        for row in _rows(source_engine, tables["university"]):
            university_for(row.get("university_name"))

    if "department" in tables:
        for row in _rows(source_engine, tables["department"]):
            university = university_for(row.get("university_name"), _clean(row.get("website")))
            if university is None:
                continue
            name = row.get("department") or row.get("school") or row.get("entity_type")
            description = _clean(row.get("school")) or _clean(row.get("entity_type"))
            department_for(university, name, description)

    if "professors" in tables:
        for row in _rows(source_engine, tables["professors"]):
            university = university_for(row.get("university_name"))
            professor_name = _clean(row.get("name"))
            if university is None or professor_name is None:
                continue
            faculty = _clean(row.get("faculty"))
            department = department_for(university, faculty) if faculty else None
            found = session.scalars(
                select(Professor).where(
                    Professor.university_id == university.id,
                    func.lower(Professor.name) == professor_name.casefold(),
                )
            ).first()
            if found is None:
                found = Professor(university_id=university.id, name=professor_name)
                session.add(found)
                counts["created_professors"] += 1
            if department is not None:
                found.department_id = department.id
            found.email = _clean(row.get("email")) or found.email
            found.designation = _clean(row.get("title")) or found.designation
            research = _clean(row.get("professor_research_interests"))
            if research:
                found.research_areas, _ = _merge_terms(found.research_areas, research)
            profile = _clean(row.get("website")) or _clean(row.get("source_url"))
            if profile:
                found.profile_url = profile
            counts["professors"] += 1

    if "program_details" in tables:
        for row in _rows(source_engine, tables["program_details"]):
            university = university_for(row.get("university_name"))
            program_name = _clean(row.get("name"))
            if university is None or program_name is None:
                continue
            degree = _clean(row.get("degree"))
            candidates = session.scalars(
                select(CourseProgram).where(
                    CourseProgram.university_id == university.id,
                    func.lower(CourseProgram.name) == program_name.casefold(),
                )
            ).all()
            found = next(
                (item for item in candidates if (item.degree_level or None) == degree), None
            )
            if found is None:
                found = CourseProgram(
                    university_id=university.id,
                    name=program_name,
                    degree_level=degree,
                )
                session.add(found)
                counts["created_programs"] += 1
            found.degree_level = degree
            found.field_of_study = _clean(row.get("department_name")) or found.field_of_study
            found.admission_requirements = (
                _clean(row.get("admission_requirements")) or found.admission_requirements
            )
            found.application_deadline = (
                _parse_date(row.get("application_deadline")) or found.application_deadline
            )
            found.application_url = _clean(row.get("source_url")) or found.application_url
            counts["programs"] += 1

    if "personal_info" in tables:
        for row in _rows(source_engine, tables["personal_info"]):
            university = university_for(row.get("university_name"))
            professor_name = _clean(row.get("name"))
            interest = _clean(row.get("research_interest"))
            if university is None or professor_name is None:
                continue
            professor = session.scalars(
                select(Professor).where(
                    Professor.university_id == university.id,
                    func.lower(Professor.name) == professor_name.casefold(),
                )
            ).first()
            if professor is None:
                continue
            counts["personal_info_matched"] += 1
            if interest is None:
                continue
            professor.research_areas, added = _merge_terms(professor.research_areas, interest)
            counts["personal_info_added"] += added

    if dry_run:
        session.rollback()
    else:
        session.commit()
    return counts
