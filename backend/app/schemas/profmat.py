from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict
from pydantic import EmailStr


class UserBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    email: EmailStr


class UserCreate(UserBase):
    password_hash: str


class User(UserBase):
    id: str
    password_hash: str
    created_at: datetime


class AcademicProfileBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    degree_level: str | None = None
    field_of_study: str | None = None
    previous_university: str | None = None
    gpa: Decimal | None = None
    graduation_year: str | None = None
    english_test_score: str | None = None


class AcademicProfileCreate(AcademicProfileBase):
    user_id: str


class AcademicProfile(AcademicProfileBase):
    id: str
    user_id: str


class ResearchProfileBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    research_interests: str | None = None
    publications: str | None = None
    skills: str | None = None
    research_experience: str | None = None
    preferred_degree: str | None = None


class ResearchProfileCreate(ResearchProfileBase):
    user_id: str


class ResearchProfile(ResearchProfileBase):
    id: str
    user_id: str


class CVBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    file_url: str
    version: str | None = None


class CVCreate(CVBase):
    user_id: str


class CV(CVBase):
    id: str
    user_id: str
    uploaded_at: datetime


class CountryBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    study_information: str | None = None
    living_cost: Decimal | None = None


class CountryCreate(CountryBase):
    country_code: str


class Country(CountryBase):
    country_code: str


class CountryPreferenceBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    priority: str | None = None


class CountryPreferenceCreate(CountryPreferenceBase):
    user_id: str
    country_code: str


class CountryPreference(CountryPreferenceBase):
    id: str
    user_id: str
    country_code: str


class VisaInformationBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    visa_type: str
    requirements: str | None = None
    processing_time: str | None = None


class VisaInformationCreate(VisaInformationBase):
    country_code: str


class VisaInformation(VisaInformationBase):
    id: str
    country_code: str
    last_updated: datetime


class UniversityBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    website: str | None = None
    ranking: str | None = None
    description: str | None = None


class UniversityCreate(UniversityBase):
    country_code: str


class University(UniversityBase):
    id: str
    country_code: str


class DepartmentBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    description: str | None = None


class DepartmentCreate(DepartmentBase):
    university_id: str


class Department(DepartmentBase):
    id: str
    university_id: str


class ProfessorBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    email: str | None = None
    designation: str | None = None
    research_areas: str | None = None
    profile_url: str | None = None


class ProfessorCreate(ProfessorBase):
    university_id: str
    department_id: str | None = None


class Professor(ProfessorBase):
    id: str
    university_id: str
    department_id: str | None = None


class CourseProgramBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    degree_level: str
    field_of_study: str | None = None
    admission_requirements: str | None = None
    application_deadline: date | None = None
    application_url: str | None = None


class CourseProgramCreate(CourseProgramBase):
    university_id: str


class CourseProgram(CourseProgramBase):
    id: str
    university_id: str


class FundingBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str
    funding_type: str
    eligibility: str | None = None
    amount: Decimal | None = None
    deadline: date | None = None
    application_url: str | None = None


class FundingCreate(FundingBase):
    university_id: str | None = None


class Funding(FundingBase):
    id: str
    university_id: str | None = None


class MatchResultBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    match_score: Decimal
    explanation: str | None = None
    status: str
    algorithm_version: str | None = None


class MatchResultCreate(MatchResultBase):
    user_id: str
    professor_id: str | None = None
    university_id: str | None = None
    course_program_id: str | None = None
    funding_id: str | None = None


class MatchResult(MatchResultBase):
    id: str
    user_id: str
    professor_id: str | None = None
    university_id: str | None = None
    course_program_id: str | None = None
    funding_id: str | None = None
    generated_at: datetime


class ProfessorOutreachBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    purpose: str
    stage: str
    planned_send_at: datetime | None = None
    sent_at: datetime | None = None
    follow_up_at: datetime | None = None
    response_status: str
    outcome: str | None = None


class ProfessorOutreachCreate(ProfessorOutreachBase):
    user_id: str
    professor_id: str
    funding_id: str | None = None


class ProfessorOutreach(ProfessorOutreachBase):
    id: str
    user_id: str
    professor_id: str
    funding_id: str | None = None
    created_at: datetime

    def update_stage(self) -> None:
        pass


class UniversityApplicationBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    application_type: str
    stage: str
    deadline: date | None = None
    submitted_at: datetime | None = None
    application_reference: str | None = None
    decision: str | None = None


class UniversityApplicationCreate(UniversityApplicationBase):
    user_id: str
    university_id: str
    course_program_id: str


class UniversityApplication(UniversityApplicationBase):
    id: str
    user_id: str
    university_id: str
    course_program_id: str
    created_at: datetime
    updated_at: datetime

    def update_stage(self) -> None:
        pass


class ChecklistBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str
    checklist_type: str
    status: str


class ChecklistCreate(ChecklistBase):
    user_id: str
    professor_outreach_id: str | None = None
    university_application_id: str | None = None


class Checklist(ChecklistBase):
    id: str
    user_id: str
    professor_outreach_id: str | None = None
    university_application_id: str | None = None
    created_at: datetime

    @property
    def progress_percent(self) -> float:
        return 0.0

    def calculate_progress(self) -> float:
        return 0.0


class ChecklistItemBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str
    description: str | None = None
    status: str
    due_date: date | None = None
    completed_at: datetime | None = None
    notes: str | None = None


class ChecklistItemCreate(ChecklistItemBase):
    checklist_id: str


class ChecklistItem(ChecklistItemBase):
    id: str
    checklist_id: str

    def mark_completed(self) -> None:
        pass


class EmailRecordBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    subject: str | None = None
    body: str | None = None
    direction: str
    sent_at: datetime | None = None
    received_at: datetime | None = None
    response_summary: str | None = None


class EmailRecordCreate(EmailRecordBase):
    outreach_id: str


class EmailRecord(EmailRecordBase):
    id: str
    outreach_id: str


class ApplicationDocumentBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_type: str
    file_url: str | None = None
    status: str
    uploaded_at: datetime | None = None


class ApplicationDocumentCreate(ApplicationDocumentBase):
    university_application_id: str


class ApplicationDocument(ApplicationDocumentBase):
    id: str
    university_application_id: str


class ProfessorOutreachStageHistoryBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    previous_stage: str | None = None
    new_stage: str
    notes: str | None = None


class ProfessorOutreachStageHistoryCreate(ProfessorOutreachStageHistoryBase):
    outreach_id: str


class ProfessorOutreachStageHistory(ProfessorOutreachStageHistoryBase):
    id: str
    outreach_id: str
    changed_at: datetime


class UniversityApplicationStageHistoryBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    previous_stage: str | None = None
    new_stage: str
    notes: str | None = None


class UniversityApplicationStageHistoryCreate(UniversityApplicationStageHistoryBase):
    application_id: str


class UniversityApplicationStageHistory(UniversityApplicationStageHistoryBase):
    id: str
    application_id: str
    changed_at: datetime


class AIApplicationStrategyBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    target_type: str
    strategy: str
    recommended_timeline: str | None = None
    model_version: str | None = None


class AIApplicationStrategyCreate(AIApplicationStrategyBase):
    user_id: str
    outreach_id: str | None = None
    application_id: str | None = None


class AIApplicationStrategy(AIApplicationStrategyBase):
    id: str
    user_id: str
    outreach_id: str | None = None
    application_id: str | None = None
    generated_at: datetime


class AIRecommendationBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    recommendation_type: str
    rationale: str | None = None
    priority: str
    status: str


class AIRecommendationCreate(AIRecommendationBase):
    strategy_id: str


class AIRecommendation(AIRecommendationBase):
    id: str
    strategy_id: str


class NewsBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str
    content: str | None = None
    source_url: str | None = None


class NewsCreate(NewsBase):
    pass


class News(NewsBase):
    id: str
    published_at: datetime | None = None


class UniversityAdvertisementBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str
    description: str | None = None
    target_url: str | None = None
    start_date: date | None = None
    end_date: date | None = None


class UniversityAdvertisementCreate(UniversityAdvertisementBase):
    university_id: str


class UniversityAdvertisement(UniversityAdvertisementBase):
    id: str
    university_id: str
