"""Response schemas for the PROFMAT domain.

These mirror the SQLAlchemy models in ``app.models`` and are used as
``response_model`` values by the API routes so that ORM instances are validated
and serialized without leaking internal SQLAlchemy state.
"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class AcademicProfileRead(ORMBase):
    id: UUID
    user_id: UUID
    degree_level: str | None = None
    field_of_study: str | None = None
    previous_university: str | None = None
    gpa: str | None = None
    graduation_year: int | None = None
    english_test_score: str | None = None


class ResearchProfileRead(ORMBase):
    id: UUID
    user_id: UUID
    research_interests: str | None = None
    publications: str | None = None
    skills: str | None = None
    research_experience: str | None = None
    preferred_degree: str | None = None


class CVRead(ORMBase):
    id: UUID
    user_id: UUID
    file_url: str
    version: str | None = None
    uploaded_at: datetime


class CountryRead(ORMBase):
    country_code: str
    name: str
    study_information: str | None = None
    living_cost: str | None = None


class CountryPreferenceRead(ORMBase):
    id: UUID
    user_id: UUID
    country_code: str
    priority: int | None = None


class VisaInformationRead(ORMBase):
    id: UUID
    country_code: str
    visa_type: str | None = None
    requirements: str | None = None
    processing_time: str | None = None
    last_updated: datetime


class UniversityRead(ORMBase):
    id: UUID
    name: str
    country_code: str
    website: str | None = None
    ranking: str | None = None
    description: str | None = None


class DepartmentRead(ORMBase):
    id: UUID
    university_id: UUID
    name: str
    description: str | None = None


class ProfessorRead(ORMBase):
    id: UUID
    university_id: UUID
    department_id: UUID | None = None
    name: str
    email: str | None = None
    designation: str | None = None
    research_areas: str | None = None
    profile_url: str | None = None


class CourseProgramRead(ORMBase):
    id: UUID
    university_id: UUID
    name: str
    degree_level: str | None = None
    field_of_study: str | None = None
    admission_requirements: str | None = None
    application_deadline: date | None = None
    application_url: str | None = None


class FundingRead(ORMBase):
    id: UUID
    university_id: UUID | None = None
    title: str
    funding_type: str | None = None
    eligibility: str | None = None
    amount: str | None = None
    deadline: date | None = None
    application_url: str | None = None


class MatchResultRead(ORMBase):
    id: UUID
    user_id: UUID
    professor_id: UUID | None = None
    university_id: UUID | None = None
    course_program_id: UUID | None = None
    funding_id: UUID | None = None
    match_score: float | None = None
    explanation: str | None = None
    status: str | None = None
    algorithm_version: str | None = None
    generated_at: datetime


class ProfessorOutreachRead(ORMBase):
    id: UUID
    user_id: UUID
    professor_id: UUID
    funding_id: UUID | None = None
    purpose: str | None = None
    stage: str | None = None
    planned_send_at: datetime | None = None
    sent_at: datetime | None = None
    follow_up_at: datetime | None = None
    response_status: str | None = None
    outcome: str | None = None


class EmailRecordRead(ORMBase):
    id: UUID
    outreach_id: UUID
    subject: str | None = None
    body: str | None = None
    direction: str | None = None
    sent_at: datetime | None = None
    received_at: datetime | None = None
    response_summary: str | None = None


class UniversityApplicationRead(ORMBase):
    id: UUID
    user_id: UUID
    university_id: UUID
    course_program_id: UUID
    application_type: str | None = None
    stage: str | None = None
    deadline: date | None = None
    submitted_at: datetime | None = None
    application_reference: str | None = None
    decision: str | None = None


class ApplicationDocumentRead(ORMBase):
    id: UUID
    university_application_id: UUID
    document_type: str | None = None
    file_url: str
    status: str | None = None
    uploaded_at: datetime


class ProfessorOutreachStageHistoryRead(ORMBase):
    id: UUID
    outreach_id: UUID
    previous_stage: str | None = None
    new_stage: str | None = None
    changed_at: datetime
    notes: str | None = None


class UniversityApplicationStageHistoryRead(ORMBase):
    id: UUID
    application_id: UUID
    previous_stage: str | None = None
    new_stage: str | None = None
    changed_at: datetime
    notes: str | None = None


class ChecklistRead(ORMBase):
    id: UUID
    user_id: UUID
    professor_outreach_id: UUID | None = None
    university_application_id: UUID | None = None
    title: str | None = None
    checklist_type: str | None = None
    status: str | None = None


class ChecklistItemRead(ORMBase):
    id: UUID
    checklist_id: UUID
    title: str
    description: str | None = None
    status: str | None = None
    due_date: date | None = None
    completed_at: datetime | None = None
    notes: str | None = None


class AIApplicationStrategyRead(ORMBase):
    id: UUID
    user_id: UUID
    target_type: str | None = None
    outreach_id: UUID | None = None
    application_id: UUID | None = None
    strategy: str | None = None
    recommended_timeline: str | None = None
    model_version: str | None = None
    generated_at: datetime


class AIRecommendationRead(ORMBase):
    id: UUID
    strategy_id: UUID
    recommendation_type: str | None = None
    rationale: str | None = None
    priority: str | None = None
    status: str | None = None


class NewsRead(ORMBase):
    id: UUID
    title: str
    content: str | None = None
    source_url: str | None = None
    published_at: datetime | None = None


class UniversityAdvertisementRead(ORMBase):
    id: UUID
    university_id: UUID
    title: str
    description: str | None = None
    target_url: str | None = None
    start_date: date | None = None
    end_date: date | None = None


class ProfessorDetailRead(ProfessorRead):
    university: UniversityRead
    department: DepartmentRead | None = None


class ProfessorPage(BaseModel):
    items: list[ProfessorDetailRead]
    total: int
    limit: int
    offset: int


class SuggestionRead(BaseModel):
    type: str
    id: UUID
    label: str
    subtitle: str | None = None


class ProfessorFiltersRead(BaseModel):
    countries: list[CountryRead]
    universities: list[UniversityRead]
    departments: list[DepartmentRead]


class PublicationRead(BaseModel):
    title: str
    venue: str | None = None
    year: int | None = None
    url: str | None = None


class ProfessorOpportunitiesRead(BaseModel):
    funding: list[FundingRead]
    programs: list[CourseProgramRead]


class HomeRead(BaseModel):
    news: list[NewsRead]
    advertisements: list[UniversityAdvertisementRead]
    featured_funding: list[FundingRead]


class HomeSummaryRead(BaseModel):
    countries: int
    universities: int
    professors: int
    programs: int
    funding: int
    news: int


class ProfileCompletenessRead(BaseModel):
    percentage: int
    completed: list[str]
    missing: list[str]
