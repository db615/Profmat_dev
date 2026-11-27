"""Idempotent demo data for the normalized PROFMAT schema.

Run with ``python -m app.manage seed`` (inside the API container) or
``python -m app.seed``. Re-running is safe: rows use deterministic UUIDs and are
updated in place rather than duplicated.
"""

from datetime import UTC, date, datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import func, select
from sqlalchemy.orm import Session

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

COUNTRIES = [
    {
        "country_code": "US",
        "name": "United States",
        "study_information": "Large research universities with many fully funded PhD programs.",
        "living_cost": "USD 12,000-20,000 per year",
    },
    {
        "country_code": "GB",
        "name": "United Kingdom",
        "study_information": (
            "Strong research culture; funded studentships via departments and UKRI."
        ),
        "living_cost": "GBP 12,000-18,000 per year",
    },
    {
        "country_code": "DE",
        "name": "Germany",
        "study_information": (
            "Low tuition and strong engineering/CS institutes; many English-taught programs."
        ),
        "living_cost": "EUR 10,000-14,000 per year",
    },
    {
        "country_code": "CA",
        "name": "Canada",
        "study_information": "Research-intensive universities with funded graduate positions.",
        "living_cost": "CAD 15,000-25,000 per year",
    },
    {
        "country_code": "AU",
        "name": "Australia",
        "study_information": "Research scholarships and strong CS/engineering groups.",
        "living_cost": "AUD 20,000-30,000 per year",
    },
    {
        "country_code": "NL",
        "name": "Netherlands",
        "study_information": "English-taught programs and collaborative research culture.",
        "living_cost": "EUR 12,000-16,000 per year",
    },
]

UNIVERSITIES = [
    {
        "key": "stanford",
        "name": "Stanford University",
        "country_code": "US",
        "website": "https://www.stanford.edu",
        "ranking": "QS #6",
        "description": "Private research university in California.",
    },
    {
        "key": "mit",
        "name": "Massachusetts Institute of Technology",
        "country_code": "US",
        "website": "https://www.mit.edu",
        "ranking": "QS #1",
        "description": "Leading institute for science and engineering.",
    },
    {
        "key": "oxford",
        "name": "University of Oxford",
        "country_code": "GB",
        "website": "https://www.ox.ac.uk",
        "ranking": "QS #3",
        "description": "Historic research university.",
    },
    {
        "key": "cambridge",
        "name": "University of Cambridge",
        "country_code": "GB",
        "website": "https://www.cam.ac.uk",
        "ranking": "QS #2",
        "description": "World-leading research and teaching.",
    },
    {
        "key": "tum",
        "name": "Technical University of Munich",
        "country_code": "DE",
        "website": "https://www.tum.de",
        "ranking": "QS #28",
        "description": "Leading German technical university.",
    },
    {
        "key": "toronto",
        "name": "University of Toronto",
        "country_code": "CA",
        "website": "https://www.utoronto.ca",
        "ranking": "QS #25",
        "description": "Canada's largest research university.",
    },
    {
        "key": "melbourne",
        "name": "University of Melbourne",
        "country_code": "AU",
        "website": "https://www.unimelb.edu.au",
        "ranking": "QS #13",
        "description": "Australia's leading research university.",
    },
    {
        "key": "tudelft",
        "name": "Delft University of Technology",
        "country_code": "NL",
        "website": "https://www.tudelft.nl",
        "ranking": "QS #47",
        "description": "The Netherlands' largest technical university.",
    },
]

DEPARTMENTS = [
    {
        "key": "stanford-cs",
        "university": "stanford",
        "name": "Computer Science",
        "description": "CS theory, AI, systems and HCI.",
    },
    {
        "key": "stanford-ee",
        "university": "stanford",
        "name": "Electrical Engineering",
        "description": "Signals, circuits and communications.",
    },
    {
        "key": "mit-cs",
        "university": "mit",
        "name": "Electrical Engineering and Computer Science",
        "description": "EECS research and teaching.",
    },
    {
        "key": "mit-ee",
        "university": "mit",
        "name": "Electrical Engineering",
        "description": "Energy, electronics and control.",
    },
    {
        "key": "oxford-cs",
        "university": "oxford",
        "name": "Computer Science",
        "description": "Algorithms, languages and verification.",
    },
    {
        "key": "cambridge-cs",
        "university": "cambridge",
        "name": "Computer Science",
        "description": "Vision, graphics and machine learning.",
    },
    {
        "key": "tum-cs",
        "university": "tum",
        "name": "Informatics",
        "description": "Data, security and software engineering.",
    },
    {
        "key": "tum-ee",
        "university": "tum",
        "name": "Electrical Engineering",
        "description": "Embedded and power systems.",
    },
    {
        "key": "toronto-cs",
        "university": "toronto",
        "name": "Computer Science",
        "description": "Machine learning and HCI.",
    },
    {
        "key": "melbourne-cs",
        "university": "melbourne",
        "name": "Computing and Information Systems",
        "description": "AI, data science and planning.",
    },
    {
        "key": "tudelft-cs",
        "university": "tudelft",
        "name": "Software Technology",
        "description": "Autonomous systems and software engineering.",
    },
]

PROFESSORS = [
    {
        "key": "alice-nguyen",
        "department": "stanford-cs",
        "name": "Alice Nguyen",
        "email": "alice.nguyen@example.edu",
        "designation": "Associate Professor",
        "research_areas": "machine learning, deep learning, computer vision, trustworthy AI",
        "profile_url": "https://example.edu/stanford/alice-nguyen",
    },
    {
        "key": "ben-carter",
        "department": "stanford-cs",
        "name": "Ben Carter",
        "email": "ben.carter@example.edu",
        "designation": "Professor",
        "research_areas": (
            "natural language processing, large language models, information retrieval"
        ),
        "profile_url": "https://example.edu/stanford/ben-carter",
    },
    {
        "key": "chloe-martin",
        "department": "stanford-ee",
        "name": "Chloe Martin",
        "email": "chloe.martin@example.edu",
        "designation": "Professor",
        "research_areas": "signal processing, wireless communications, edge computing",
        "profile_url": "https://example.edu/stanford/chloe-martin",
    },
    {
        "key": "daniel-okafor",
        "department": "mit-cs",
        "name": "Daniel Okafor",
        "email": "daniel.okafor@example.edu",
        "designation": "Professor",
        "research_areas": "distributed systems, cloud computing, fault tolerance",
        "profile_url": "https://example.edu/mit/daniel-okafor",
    },
    {
        "key": "elena-petrova",
        "department": "mit-cs",
        "name": "Elena Petrova",
        "email": "elena.petrova@example.edu",
        "designation": "Associate Professor",
        "research_areas": "robotics, reinforcement learning, control systems",
        "profile_url": "https://example.edu/mit/elena-petrova",
    },
    {
        "key": "farhan-ali",
        "department": "mit-ee",
        "name": "Farhan Ali",
        "email": "farhan.ali@example.edu",
        "designation": "Professor",
        "research_areas": "power electronics, renewable energy, smart grids",
        "profile_url": "https://example.edu/mit/farhan-ali",
    },
    {
        "key": "grace-thompson",
        "department": "oxford-cs",
        "name": "Grace Thompson",
        "email": "grace.thompson@example.edu",
        "designation": "Professor",
        "research_areas": "programming languages, compilers, formal verification",
        "profile_url": "https://example.edu/oxford/grace-thompson",
    },
    {
        "key": "henry-wong",
        "department": "cambridge-cs",
        "name": "Henry Wong",
        "email": "henry.wong@example.edu",
        "designation": "Professor",
        "research_areas": "computer vision, medical imaging, multimodal learning",
        "profile_url": "https://example.edu/cambridge/henry-wong",
    },
    {
        "key": "isabel-garcia",
        "department": "tum-cs",
        "name": "Isabel Garcia",
        "email": "isabel.garcia@example.edu",
        "designation": "Professor",
        "research_areas": "data mining, recommender systems, graph learning",
        "profile_url": "https://example.edu/tum/isabel-garcia",
    },
    {
        "key": "jonas-mueller",
        "department": "tum-cs",
        "name": "Jonas Mueller",
        "email": "jonas.mueller@example.edu",
        "designation": "Associate Professor",
        "research_areas": "cybersecurity, privacy, applied cryptography",
        "profile_url": "https://example.edu/tum/jonas-mueller",
    },
    {
        "key": "kavya-rao",
        "department": "tum-ee",
        "name": "Kavya Rao",
        "email": "kavya.rao@example.edu",
        "designation": "Professor",
        "research_areas": "embedded systems, hardware security, internet of things",
        "profile_url": "https://example.edu/tum/kavya-rao",
    },
    {
        "key": "liam-obrien",
        "department": "toronto-cs",
        "name": "Liam O'Brien",
        "email": "liam.obrien@example.edu",
        "designation": "Professor",
        "research_areas": "machine learning, optimization, probabilistic models",
        "profile_url": "https://example.edu/toronto/liam-obrien",
    },
    {
        "key": "mia-chen",
        "department": "toronto-cs",
        "name": "Mia Chen",
        "email": "mia.chen@example.edu",
        "designation": "Associate Professor",
        "research_areas": "human-computer interaction, accessibility, user experience",
        "profile_url": "https://example.edu/toronto/mia-chen",
    },
    {
        "key": "noah-silva",
        "department": "melbourne-cs",
        "name": "Noah Silva",
        "email": "noah.silva@example.edu",
        "designation": "Professor",
        "research_areas": "artificial intelligence, multi-agent systems, automated planning",
        "profile_url": "https://example.edu/melbourne/noah-silva",
    },
    {
        "key": "olivia-brown",
        "department": "melbourne-cs",
        "name": "Olivia Brown",
        "email": "olivia.brown@example.edu",
        "designation": "Associate Professor",
        "research_areas": "data science, causal inference, health analytics",
        "profile_url": "https://example.edu/melbourne/olivia-brown",
    },
    {
        "key": "priya-sharma",
        "department": "tudelft-cs",
        "name": "Priya Sharma",
        "email": "priya.sharma@example.edu",
        "designation": "Professor",
        "research_areas": "computer vision, autonomous systems, sensor fusion",
        "profile_url": "https://example.edu/tudelft/priya-sharma",
    },
    {
        "key": "quentin-lee",
        "department": "tudelft-cs",
        "name": "Quentin Lee",
        "email": "quentin.lee@example.edu",
        "designation": "Associate Professor",
        "research_areas": "software engineering, testing, program analysis",
        "profile_url": "https://example.edu/tudelft/quentin-lee",
    },
]

PROGRAMS = [
    {
        "key": "stanford-msc-cs",
        "university": "stanford",
        "name": "MS in Computer Science",
        "degree_level": "MSc",
        "field_of_study": "Computer Science",
        "admission_requirements": "Strong CS background; GRE optional; TOEFL/IELTS.",
        "application_deadline": date(2027, 1, 5),
        "application_url": "https://example.edu/stanford/msc-cs",
    },
    {
        "key": "stanford-phd-cs",
        "university": "stanford",
        "name": "PhD in Computer Science",
        "degree_level": "PhD",
        "field_of_study": "Computer Science",
        "admission_requirements": "Research experience and strong references.",
        "application_deadline": date(2026, 12, 1),
        "application_url": "https://example.edu/stanford/phd-cs",
    },
    {
        "key": "mit-phd-eecs",
        "university": "mit",
        "name": "PhD in Electrical Engineering and Computer Science",
        "degree_level": "PhD",
        "field_of_study": "EECS",
        "admission_requirements": "Strong quantitative background and research fit.",
        "application_deadline": date(2026, 12, 15),
        "application_url": "https://example.edu/mit/phd-eecs",
    },
    {
        "key": "oxford-msc-cs",
        "university": "oxford",
        "name": "MSc in Advanced Computer Science",
        "degree_level": "MSc",
        "field_of_study": "Computer Science",
        "admission_requirements": "First-class undergraduate degree in CS or related field.",
        "application_deadline": date(2027, 1, 20),
        "application_url": "https://example.edu/oxford/msc-cs",
    },
    {
        "key": "cambridge-mphil-cs",
        "university": "cambridge",
        "name": "MPhil in Computer Science",
        "degree_level": "MPhil",
        "field_of_study": "Computer Science",
        "admission_requirements": "Strong undergraduate record and research potential.",
        "application_deadline": date(2027, 1, 4),
        "application_url": "https://example.edu/cambridge/mphil-cs",
    },
    {
        "key": "tum-msc-informatics",
        "university": "tum",
        "name": "MSc in Informatics",
        "degree_level": "MSc",
        "field_of_study": "Informatics",
        "admission_requirements": "Bachelor in informatics or equivalent.",
        "application_deadline": date(2027, 1, 15),
        "application_url": "https://example.edu/tum/msc-informatics",
    },
    {
        "key": "tum-msc-ee",
        "university": "tum",
        "name": "MSc in Electrical Engineering",
        "degree_level": "MSc",
        "field_of_study": "Electrical Engineering",
        "admission_requirements": "Bachelor in electrical engineering or related field.",
        "application_deadline": date(2027, 1, 15),
        "application_url": "https://example.edu/tum/msc-ee",
    },
    {
        "key": "toronto-msc-cs",
        "university": "toronto",
        "name": "MSc in Computer Science",
        "degree_level": "MSc",
        "field_of_study": "Computer Science",
        "admission_requirements": "Strong CS background; supervisor match recommended.",
        "application_deadline": date(2027, 1, 10),
        "application_url": "https://example.edu/toronto/msc-cs",
    },
    {
        "key": "toronto-phd-cs",
        "university": "toronto",
        "name": "PhD in Computer Science",
        "degree_level": "PhD",
        "field_of_study": "Computer Science",
        "admission_requirements": "Research experience and identified supervisor.",
        "application_deadline": date(2026, 12, 1),
        "application_url": "https://example.edu/toronto/phd-cs",
    },
    {
        "key": "melbourne-msc-cs",
        "university": "melbourne",
        "name": "Master of Computer Science",
        "degree_level": "MSc",
        "field_of_study": "Computer Science",
        "admission_requirements": "Undergraduate degree with strong computing component.",
        "application_deadline": date(2027, 2, 1),
        "application_url": "https://example.edu/melbourne/msc-cs",
    },
    {
        "key": "tudelft-msc-cs",
        "university": "tudelft",
        "name": "MSc in Computer Science",
        "degree_level": "MSc",
        "field_of_study": "Computer Science",
        "admission_requirements": "Bachelor in CS or closely related field.",
        "application_deadline": date(2026, 12, 1),
        "application_url": "https://example.edu/tudelft/msc-cs",
    },
]

FUNDING = [
    {
        "key": "stanford-knight-hennessy",
        "university": "stanford",
        "title": "Knight-Hennessy Scholars",
        "funding_type": "Scholarship",
        "eligibility": "Graduate students with leadership potential.",
        "amount": "Full tuition + stipend",
        "deadline": date(2026, 10, 8),
        "application_url": "https://example.edu/stanford/khs",
    },
    {
        "key": "mit-presidential",
        "university": "mit",
        "title": "Presidential Fellowship",
        "funding_type": "Fellowship",
        "eligibility": "Incoming PhD students.",
        "amount": "Full tuition + stipend",
        "deadline": date(2026, 12, 15),
        "application_url": "https://example.edu/mit/fellowship",
    },
    {
        "key": "oxford-clarendon",
        "university": "oxford",
        "title": "Clarendon Fund Scholarship",
        "funding_type": "Scholarship",
        "eligibility": "Outstanding graduate applicants.",
        "amount": "Full tuition + stipend",
        "deadline": date(2027, 1, 20),
        "application_url": "https://example.edu/oxford/clarendon",
    },
    {
        "key": "daad-epos",
        "university": None,
        "title": "DAAD EPOS Scholarship",
        "funding_type": "Scholarship",
        "eligibility": "Graduates from developing countries.",
        "amount": "EUR 1,200 per month + travel",
        "deadline": date(2026, 9, 30),
        "application_url": "https://example.edu/daad/epos",
    },
    {
        "key": "tudelft-effen",
        "university": "tudelft",
        "title": "Justus and Louise van Effen Excellence Scholarship",
        "funding_type": "Scholarship",
        "eligibility": "Non-EU MSc applicants.",
        "amount": "EUR 15,000",
        "deadline": date(2026, 12, 1),
        "application_url": "https://example.edu/tudelft/effen",
    },
]

NEWS = [
    {
        "key": "intake-2027",
        "title": "Applications open for the 2027 graduate intake",
        "content": (
            "Several partner universities have opened applications for MSc and PhD "
            "programs starting in 2027."
        ),
        "source_url": "https://example.edu/news/intake-2027",
        "published_at": datetime(2026, 11, 1, tzinfo=UTC),
    },
    {
        "key": "tum-ai-centre",
        "title": "New AI research centre announced at TUM",
        "content": (
            "The Technical University of Munich announced a new interdisciplinary centre "
            "for applied AI."
        ),
        "source_url": "https://example.edu/news/tum-ai-centre",
        "published_at": datetime(2026, 10, 20, tzinfo=UTC),
    },
    {
        "key": "scholarship-deadlines",
        "title": "Scholarship deadlines to watch this season",
        "content": (
            "A roundup of major graduate scholarships with deadlines in late 2026 and early 2027."
        ),
        "source_url": "https://example.edu/news/scholarship-deadlines",
        "published_at": datetime(2026, 10, 5, tzinfo=UTC),
    },
]

ADVERTISEMENTS = [
    {
        "key": "stanford-ad",
        "university": "stanford",
        "title": "Stanford Graduate Open House",
        "description": "Meet faculty and current students at the virtual open house.",
        "target_url": "https://example.edu/stanford/open-house",
        "start_date": date(2026, 11, 1),
        "end_date": date(2027, 1, 31),
    },
    {
        "key": "tudelft-ad",
        "university": "tudelft",
        "title": "TU Delft MSc Information Session",
        "description": "Learn about MSc programs in software technology and AI.",
        "target_url": "https://example.edu/tudelft/info-session",
        "start_date": date(2026, 11, 15),
        "end_date": date(2027, 2, 28),
    },
]

VISAS = [
    {
        "key": "us-f1",
        "country_code": "US",
        "visa_type": "F-1 Student Visa",
        "requirements": "I-20, proof of funding, SEVIS fee, DS-160.",
        "processing_time": "3-8 weeks",
    },
    {
        "key": "gb-student",
        "country_code": "GB",
        "visa_type": "Student Visa",
        "requirements": "CAS, proof of funds, English proficiency.",
        "processing_time": "3 weeks",
    },
    {
        "key": "de-national",
        "country_code": "DE",
        "visa_type": "National Visa for Study Purposes",
        "requirements": "Admission letter, blocked account, health insurance.",
        "processing_time": "6-12 weeks",
    },
    {
        "key": "ca-study-permit",
        "country_code": "CA",
        "visa_type": "Study Permit",
        "requirements": "Acceptance letter, proof of funds, medical exam.",
        "processing_time": "4-12 weeks",
    },
    {
        "key": "au-subclass-500",
        "country_code": "AU",
        "visa_type": "Subclass 500 Student Visa",
        "requirements": "CoE, proof of funds, health insurance.",
        "processing_time": "4-8 weeks",
    },
    {
        "key": "nl-mvv",
        "country_code": "NL",
        "visa_type": "MVV + Residence Permit",
        "requirements": "Admission letter, proof of funds, sponsor declaration.",
        "processing_time": "2-4 weeks",
    },
]


def _id(kind: str, key: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"profmat:{kind}:{key}")


def _upsert(session: Session, model, pk_name: str, pk_value, values: dict) -> None:
    instance = session.get(model, pk_value)
    if instance is None:
        session.add(model(**{pk_name: pk_value}, **values))
        return
    for field, value in values.items():
        setattr(instance, field, value)


def seed_database(session: Session) -> dict[str, int]:
    """Insert or update the demo catalog and return per-table row counts."""
    for country in COUNTRIES:
        _upsert(
            session,
            Country,
            "country_code",
            country["country_code"],
            {key: value for key, value in country.items() if key != "country_code"},
        )

    universities: dict[str, UUID] = {}
    for university in UNIVERSITIES:
        values = {key: value for key, value in university.items() if key != "key"}
        university_id = _id("university", university["key"])
        universities[university["key"]] = university_id
        _upsert(session, University, "id", university_id, values)

    departments: dict[str, UUID] = {}
    for department in DEPARTMENTS:
        values = {key: value for key, value in department.items() if key != "key"}
        values["university_id"] = universities[values.pop("university")]
        department_id = _id("department", department["key"])
        departments[department["key"]] = department_id
        _upsert(session, Department, "id", department_id, values)

    for professor in PROFESSORS:
        values = {key: value for key, value in professor.items() if key != "key"}
        department_id = departments[values.pop("department")]
        values["university_id"] = session.get(Department, department_id).university_id
        values["department_id"] = department_id
        _upsert(session, Professor, "id", _id("professor", professor["key"]), values)

    for program in PROGRAMS:
        values = {key: value for key, value in program.items() if key != "key"}
        values["university_id"] = universities[values.pop("university")]
        _upsert(session, CourseProgram, "id", _id("program", program["key"]), values)

    for funding in FUNDING:
        values = {key: value for key, value in funding.items() if key != "key"}
        university_key = values.pop("university")
        values["university_id"] = universities[university_key] if university_key else None
        _upsert(session, Funding, "id", _id("funding", funding["key"]), values)

    for article in NEWS:
        values = {key: value for key, value in article.items() if key != "key"}
        _upsert(session, News, "id", _id("news", article["key"]), values)

    for advertisement in ADVERTISEMENTS:
        values = {key: value for key, value in advertisement.items() if key != "key"}
        values["university_id"] = universities[values.pop("university")]
        _upsert(
            session,
            UniversityAdvertisement,
            "id",
            _id("advertisement", advertisement["key"]),
            values,
        )

    for visa in VISAS:
        values = {key: value for key, value in visa.items() if key != "key"}
        values["last_updated"] = datetime(2026, 11, 1, tzinfo=UTC)
        _upsert(session, VisaInformation, "id", _id("visa", visa["key"]), values)

    session.commit()

    models = {
        "countries": Country,
        "universities": University,
        "departments": Department,
        "professors": Professor,
        "programs": CourseProgram,
        "funding": Funding,
        "news": News,
        "advertisements": UniversityAdvertisement,
        "visas": VisaInformation,
    }
    return {
        name: session.scalar(select(func.count()).select_from(model))
        for name, model in models.items()
    }


def main() -> None:
    from sqlalchemy.orm import sessionmaker

    from app.core.config import Settings
    from app.core.database import create_database_engine

    engine = create_database_engine(Settings().database_url)
    with sessionmaker(bind=engine, expire_on_commit=False)() as session:
        counts = seed_database(session)
    engine.dispose()
    print("Seeded demo data: " + ", ".join(f"{name}={count}" for name, count in counts.items()))


if __name__ == "__main__":
    main()
