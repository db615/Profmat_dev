from datetime import date

import pytest
from sqlalchemy import (
    Column,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    func,
    select,
)
from sqlalchemy.pool import StaticPool

from app.etl import sync_crawler
from app.models import CourseProgram, Department, Professor, University
from app.seed import seed_database


def crawler_metadata() -> MetaData:
    metadata = MetaData()
    Table(
        "university",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("university_name", String(255)),
    )
    Table(
        "department",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("university_name", String(100)),
        Column("entity_type", String(30)),
        Column("school", String(150)),
        Column("department", String(150)),
        Column("website", String(250)),
        Column("source_url", String(250)),
    )
    Table(
        "professors",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String(50)),
        Column("email", String(75)),
        Column("faculty", String(250)),
        Column("website", String(150)),
        Column("university_name", String(150)),
        Column("source_url", String(250)),
        Column("title", Text),
        Column("image_link", String(255)),
        Column("professor_research_interests", Text),
    )
    Table(
        "personal_info",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("university_name", String(100)),
        Column("name", String(100)),
        Column("department_name", String(150)),
        Column("award", String(100)),
        Column("publication", String(2000)),
        Column("research_interest", String(200)),
        Column("source_url", String(250)),
    )
    Table(
        "program_details",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("source_url", String(250)),
        Column("university_name", String(100)),
        Column("department_name", String(100)),
        Column("name", String(100)),
        Column("degree", String(250)),
        Column("duration", String(100)),
        Column("description", Text),
        Column("admission_requirements", Text),
        Column("application_deadline", String(100)),
        Column("tuition_fees", String(100)),
        Column("scholarships_available", Text),
    )
    return metadata


@pytest.fixture
def source_engine():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    crawler_metadata().create_all(engine)
    yield engine
    engine.dispose()


def seed_source(engine):
    tables = crawler_metadata().tables
    with engine.begin() as connection:
        connection.execute(
            tables["university"].insert(),
            [{"university_name": "Northwest University"}],
        )
        connection.execute(
            tables["department"].insert(),
            [
                {
                    "university_name": "Northwest University",
                    "entity_type": "department",
                    "school": "Engineering",
                    "department": "Computer Science",
                    "website": "https://nwu.example.edu/cs",
                }
            ],
        )
        connection.execute(
            tables["professors"].insert(),
            [
                {
                    "name": "Ada Lovelace",
                    "email": "ada@nwu.example.edu",
                    "faculty": "Computer Science",
                    "website": "https://nwu.example.edu/ada",
                    "university_name": "Northwest University",
                    "source_url": "https://nwu.example.edu/people/ada",
                    "title": "Professor",
                    "professor_research_interests": "machine learning, algorithms",
                }
            ],
        )
        connection.execute(
            tables["personal_info"].insert(),
            [
                {
                    "university_name": "Northwest University",
                    "name": "Ada Lovelace",
                    "research_interest": "computer vision",
                }
            ],
        )
        connection.execute(
            tables["program_details"].insert(),
            [
                {
                    "source_url": "https://nwu.example.edu/msc",
                    "university_name": "Northwest University",
                    "department_name": "Computer Science",
                    "name": "MSc Computer Science",
                    "degree": "MSc",
                    "admission_requirements": "BSc with 3.0 GPA",
                    "application_deadline": "2027-01-15",
                    "tuition_fees": "10000",
                }
            ],
        )


def test_sync_crawler_maps_and_is_idempotent(source_engine, session):
    seed_database(session)
    seed_source(source_engine)

    counts = sync_crawler(session, source_engine, default_country_code="US")
    assert counts["universities"] == 1
    assert counts["departments"] == 1
    assert counts["professors"] == 1
    assert counts["programs"] == 1
    assert counts["personal_info_matched"] == 1
    assert counts["personal_info_added"] == 1

    university = session.scalars(
        select(University).where(University.name == "Northwest University")
    ).one()
    assert university.country_code == "US"
    assert university.website == "https://nwu.example.edu/cs"

    department = session.scalars(
        select(Department).where(
            Department.university_id == university.id,
            Department.name == "Computer Science",
        )
    ).one()
    professor = session.scalars(select(Professor).where(Professor.name == "Ada Lovelace")).one()
    assert professor.university_id == university.id
    assert professor.department_id == department.id
    assert professor.email == "ada@nwu.example.edu"
    assert professor.designation == "Professor"
    assert professor.profile_url == "https://nwu.example.edu/ada"
    assert "machine learning" in professor.research_areas
    assert "computer vision" in professor.research_areas

    program = session.scalars(
        select(CourseProgram).where(CourseProgram.name == "MSc Computer Science")
    ).one()
    assert program.university_id == university.id
    assert program.degree_level == "MSc"
    assert program.field_of_study == "Computer Science"
    assert program.admission_requirements == "BSc with 3.0 GPA"
    assert program.application_deadline == date(2027, 1, 15)
    assert program.application_url == "https://nwu.example.edu/msc"

    second = sync_crawler(session, source_engine, default_country_code="US")
    assert second["universities"] == counts["universities"]
    assert second["professors"] == counts["professors"]
    assert second["created_universities"] == 0
    assert second["created_professors"] == 0
    assert second["personal_info_added"] == 0
    assert (
        session.scalar(
            select(func.count()).select_from(Professor).where(Professor.name == "Ada Lovelace")
        )
        == 1
    )
    assert (
        session.scalar(
            select(func.count())
            .select_from(CourseProgram)
            .where(CourseProgram.name == "MSc Computer Science")
        )
        == 1
    )


def test_sync_crawler_requires_seeded_country(source_engine, session):
    with pytest.raises(ValueError, match="not seeded"):
        sync_crawler(session, source_engine, default_country_code="ZZ")


def test_sync_crawler_without_raw_tables_is_noop(session):
    seed_database(session)
    empty_engine = create_engine("sqlite+pysqlite://", poolclass=StaticPool)
    try:
        counts = sync_crawler(session, empty_engine, default_country_code="US")
        assert counts["universities"] == 0
        assert counts["professors"] == 0
        assert counts["programs"] == 0
    finally:
        empty_engine.dispose()


def test_sync_crawler_dry_run_does_not_persist(source_engine, session):
    seed_database(session)
    seed_source(source_engine)

    counts = sync_crawler(session, source_engine, default_country_code="US", dry_run=True)
    assert counts["professors"] == 1
    assert (
        session.scalars(select(Professor).where(Professor.name == "Ada Lovelace")).first() is None
    )
