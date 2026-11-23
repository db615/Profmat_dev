from datetime import datetime, date
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, UTCDateTime, utcnow


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('USER', 'ADMIN')", name="ck_users_role"),
        CheckConstraint(
            "password_hash IS NOT NULL OR google_sub IS NOT NULL", name="ck_users_identity"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    full_name: Mapped[str | None] = mapped_column(String(200))
    password_hash: Mapped[str | None] = mapped_column(String(255))
    google_sub: Mapped[str | None] = mapped_column(String(255), unique=True)
    role: Mapped[str] = mapped_column(String(16), default="USER")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)


class RefreshSession(Base):
    __tablename__ = "refresh_sessions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    family_id: Mapped[UUID] = mapped_column(index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime())
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    used_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime())


class GoogleChallenge(Base):
    __tablename__ = "google_challenges"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    nonce_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime())


class AuthRateLimit(Base):
    __tablename__ = "auth_rate_limits"

    bucket_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    attempts: Mapped[int] = mapped_column(Integer)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)


# PROFMAT tables
class AcademicProfile(Base):
    __tablename__ = "academic_profiles"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    degree_level: Mapped[str | None] = mapped_column(String(100))
    field_of_study: Mapped[str | None] = mapped_column(String(200))
    previous_university: Mapped[str | None] = mapped_column(String(300))
    gpa: Mapped[str | None] = mapped_column(String(50))
    graduation_year: Mapped[int | None] = mapped_column(Integer)
    english_test_score: Mapped[str | None] = mapped_column(String(100))


class ResearchProfile(Base):
    __tablename__ = "research_profiles"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    research_interests: Mapped[str | None] = mapped_column(Text)
    publications: Mapped[str | None] = mapped_column(Text)
    skills: Mapped[str | None] = mapped_column(Text)
    research_experience: Mapped[str | None] = mapped_column(Text)
    preferred_degree: Mapped[str | None] = mapped_column(String(100))


class CV(Base):
    __tablename__ = "cvs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    file_url: Mapped[str] = mapped_column(String(1000))
    version: Mapped[str | None] = mapped_column(String(50))
    uploaded_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)


class Country(Base):
    __tablename__ = "countries"

    country_code: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    study_information: Mapped[str | None] = mapped_column(Text)
    living_cost: Mapped[str | None] = mapped_column(String(100))


class CountryPreference(Base):
    __tablename__ = "country_preferences"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    country_code: Mapped[str] = mapped_column(ForeignKey("countries.country_code"), index=True)
    priority: Mapped[int | None] = mapped_column(Integer)


class VisaInformation(Base):
    __tablename__ = "visa_information"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    country_code: Mapped[str] = mapped_column(ForeignKey("countries.country_code"), index=True)
    visa_type: Mapped[str | None] = mapped_column(String(100))
    requirements: Mapped[str | None] = mapped_column(Text)
    processing_time: Mapped[str | None] = mapped_column(String(100))
    last_updated: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)


class University(Base):
    __tablename__ = "universities"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(300))
    country_code: Mapped[str] = mapped_column(ForeignKey("countries.country_code"), index=True)
    website: Mapped[str | None] = mapped_column(String(500))
    ranking: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    university_id: Mapped[UUID] = mapped_column(ForeignKey("universities.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)


class Professor(Base):
    __tablename__ = "professors"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    university_id: Mapped[UUID] = mapped_column(ForeignKey("universities.id", ondelete="CASCADE"), index=True)
    department_id: Mapped[UUID | None] = mapped_column(ForeignKey("departments.id", ondelete="SET NULL"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(320))
    designation: Mapped[str | None] = mapped_column(String(200))
    research_areas: Mapped[str | None] = mapped_column(Text)
    profile_url: Mapped[str | None] = mapped_column(String(500))


class CourseProgram(Base):
    __tablename__ = "course_programs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    university_id: Mapped[UUID] = mapped_column(ForeignKey("universities.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(300))
    degree_level: Mapped[str | None] = mapped_column(String(100))
    field_of_study: Mapped[str | None] = mapped_column(String(200))
    admission_requirements: Mapped[str | None] = mapped_column(Text)
    application_deadline: Mapped[date | None] = mapped_column()
    application_url: Mapped[str | None] = mapped_column(String(500))


class Funding(Base):
    __tablename__ = "fundings"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    university_id: Mapped[UUID | None] = mapped_column(ForeignKey("universities.id", ondelete="SET NULL"), index=True)
    title: Mapped[str] = mapped_column(String(300))
    funding_type: Mapped[str | None] = mapped_column(String(100))
    eligibility: Mapped[str | None] = mapped_column(Text)
    amount: Mapped[str | None] = mapped_column(String(100))
    deadline: Mapped[date | None] = mapped_column()
    application_url: Mapped[str | None] = mapped_column(String(500))


class MatchResult(Base):
    __tablename__ = "match_results"
    __table_args__ = (
        CheckConstraint(
            "(professor_id IS NOT NULL AND university_id IS NULL AND course_program_id IS NULL AND funding_id IS NULL) OR "
            "(professor_id IS NULL AND university_id IS NOT NULL AND course_program_id IS NULL AND funding_id IS NULL) OR "
            "(professor_id IS NULL AND university_id IS NULL AND course_program_id IS NOT NULL AND funding_id IS NULL) OR "
            "(professor_id IS NULL AND university_id IS NULL AND course_program_id IS NULL AND funding_id IS NOT NULL)",
            name="ck_match_results_exactly_one",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    professor_id: Mapped[UUID | None] = mapped_column(ForeignKey("professors.id", ondelete="SET NULL"))
    university_id: Mapped[UUID | None] = mapped_column(ForeignKey("universities.id", ondelete="SET NULL"))
    course_program_id: Mapped[UUID | None] = mapped_column(ForeignKey("course_programs.id", ondelete="SET NULL"))
    funding_id: Mapped[UUID | None] = mapped_column(ForeignKey("fundings.id", ondelete="SET NULL"))
    match_score: Mapped[float | None] = mapped_column()
    explanation: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(String(50))
    algorithm_version: Mapped[str | None] = mapped_column(String(50))
    generated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)


class ProfessorOutreach(Base):
    __tablename__ = "professor_outreach"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    professor_id: Mapped[UUID] = mapped_column(ForeignKey("professors.id", ondelete="CASCADE"), index=True)
    funding_id: Mapped[UUID | None] = mapped_column(ForeignKey("fundings.id", ondelete="SET NULL"))
    purpose: Mapped[str | None] = mapped_column(Text)
    stage: Mapped[str | None] = mapped_column(String(100))
    planned_send_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    sent_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    follow_up_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    response_status: Mapped[str | None] = mapped_column(String(50))
    outcome: Mapped[str | None] = mapped_column(String(100))


class EmailRecord(Base):
    __tablename__ = "email_records"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    outreach_id: Mapped[UUID] = mapped_column(ForeignKey("professor_outreach.id", ondelete="CASCADE"), index=True)
    subject: Mapped[str | None] = mapped_column(String(500))
    body: Mapped[str | None] = mapped_column(Text)
    direction: Mapped[str | None] = mapped_column(String(20))
    sent_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    received_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    response_summary: Mapped[str | None] = mapped_column(Text)


class ProfessorOutreachStageHistory(Base):
    __tablename__ = "professor_outreach_stage_history"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    outreach_id: Mapped[UUID] = mapped_column(ForeignKey("professor_outreach.id", ondelete="CASCADE"), index=True)
    previous_stage: Mapped[str | None] = mapped_column(String(100))
    new_stage: Mapped[str | None] = mapped_column(String(100))
    changed_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    notes: Mapped[str | None] = mapped_column(Text)


class UniversityApplication(Base):
    __tablename__ = "university_applications"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    university_id: Mapped[UUID] = mapped_column(ForeignKey("universities.id", ondelete="CASCADE"), index=True)
    course_program_id: Mapped[UUID] = mapped_column(ForeignKey("course_programs.id", ondelete="CASCADE"), index=True)
    application_type: Mapped[str | None] = mapped_column(String(100))
    stage: Mapped[str | None] = mapped_column(String(100))
    deadline: Mapped[date | None] = mapped_column()
    submitted_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    application_reference: Mapped[str | None] = mapped_column(String(200))
    decision: Mapped[str | None] = mapped_column(String(100))


class ApplicationDocument(Base):
    __tablename__ = "application_documents"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    university_application_id: Mapped[UUID] = mapped_column(ForeignKey("university_applications.id", ondelete="CASCADE"), index=True)
    document_type: Mapped[str | None] = mapped_column(String(100))
    file_url: Mapped[str] = mapped_column(String(1000))
    status: Mapped[str | None] = mapped_column(String(50))
    uploaded_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)


class UniversityApplicationStageHistory(Base):
    __tablename__ = "university_application_stage_history"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    application_id: Mapped[UUID] = mapped_column(ForeignKey("university_applications.id", ondelete="CASCADE"), index=True)
    previous_stage: Mapped[str | None] = mapped_column(String(100))
    new_stage: Mapped[str | None] = mapped_column(String(100))
    changed_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    notes: Mapped[str | None] = mapped_column(Text)


class Checklist(Base):
    __tablename__ = "checklists"
    __table_args__ = (
        CheckConstraint(
            "(professor_outreach_id IS NOT NULL AND university_application_id IS NULL) OR "
            "(professor_outreach_id IS NULL AND university_application_id IS NOT NULL)",
            name="ck_checklists_exactly_one",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    professor_outreach_id: Mapped[UUID | None] = mapped_column(ForeignKey("professor_outreach.id", ondelete="CASCADE"))
    university_application_id: Mapped[UUID | None] = mapped_column(ForeignKey("university_applications.id", ondelete="CASCADE"))
    title: Mapped[str | None] = mapped_column(String(300))
    checklist_type: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str | None] = mapped_column(String(50))


class ChecklistItem(Base):
    __tablename__ = "checklist_items"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    checklist_id: Mapped[UUID] = mapped_column(ForeignKey("checklists.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(String(50))
    due_date: Mapped[date | None] = mapped_column()
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    notes: Mapped[str | None] = mapped_column(Text)


class AIApplicationStrategy(Base):
    __tablename__ = "ai_application_strategies"
    __table_args__ = (
        CheckConstraint(
            "(outreach_id IS NOT NULL AND application_id IS NULL) OR "
            "(outreach_id IS NULL AND application_id IS NOT NULL)",
            name="ck_ai_strategies_exactly_one",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    target_type: Mapped[str | None] = mapped_column(String(50))
    outreach_id: Mapped[UUID | None] = mapped_column(ForeignKey("professor_outreach.id", ondelete="CASCADE"))
    application_id: Mapped[UUID | None] = mapped_column(ForeignKey("university_applications.id", ondelete="CASCADE"))
    strategy: Mapped[str | None] = mapped_column(Text)
    recommended_timeline: Mapped[str | None] = mapped_column(Text)
    model_version: Mapped[str | None] = mapped_column(String(100))
    generated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)


class AIRecommendation(Base):
    __tablename__ = "ai_recommendations"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    strategy_id: Mapped[UUID] = mapped_column(ForeignKey("ai_application_strategies.id", ondelete="CASCADE"), index=True)
    recommendation_type: Mapped[str | None] = mapped_column(String(100))
    rationale: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[str | None] = mapped_column(String(50))


class News(Base):
    __tablename__ = "news"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(500))
    content: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(String(1000))
    published_at: Mapped[datetime | None] = mapped_column(UTCDateTime())


class UniversityAdvertisement(Base):
    __tablename__ = "university_advertisements"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    university_id: Mapped[UUID] = mapped_column(ForeignKey("universities.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    target_url: Mapped[str | None] = mapped_column(String(1000))
    start_date: Mapped[date | None] = mapped_column()
    end_date: Mapped[date | None] = mapped_column()
