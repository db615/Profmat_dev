"""Create Profmat schema tables if not existing."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0003_profmat_schema"
down_revision = "0002_mariadb_datetime_precision"
branch_labels = None
depends_on = None

REQUIRED_COLUMNS = {
    "universities": {"id", "name", "country_code", "website", "ranking", "description"},
    "departments": {"id", "university_id", "name", "description"},
    "professors": {
        "id",
        "university_id",
        "department_id",
        "name",
        "email",
        "designation",
        "research_areas",
        "profile_url",
    },
    "course_programs": {
        "id",
        "university_id",
        "name",
        "degree_level",
        "field_of_study",
        "admission_requirements",
        "application_deadline",
        "application_url",
    },
    "fundings": {
        "id",
        "university_id",
        "title",
        "funding_type",
        "eligibility",
        "amount",
        "deadline",
        "application_url",
    },
}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())

    def create_if_missing(table_name: str, create_fn):
        if table_name not in existing_tables:
            create_fn()
            return
        expected = REQUIRED_COLUMNS.get(table_name)
        if expected is None:
            return
        actual = {column["name"] for column in inspector.get_columns(table_name)}
        missing = expected - actual
        if missing:
            raise RuntimeError(
                f"Existing table {table_name!r} is incompatible with the Profmat schema; "
                f"missing columns: {', '.join(sorted(missing))}. This usually means raw "
                "crawler tables share the same name. Move raw data to a separate "
                "schema/database (or prefix the raw tables) before running this migration."
            )

    def _create_academic_profiles():
        op.create_table(
            "academic_profiles",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column(
                "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
            ),
            sa.Column("degree_level", sa.String(100)),
            sa.Column("field_of_study", sa.String(200)),
            sa.Column("previous_university", sa.String(300)),
            sa.Column("gpa", sa.String(50)),
            sa.Column("graduation_year", sa.Integer()),
            sa.Column("english_test_score", sa.String(100)),
        )
        op.create_index("ix_academic_profiles_user_id", "academic_profiles", ["user_id"])

    create_if_missing("academic_profiles", _create_academic_profiles)

    def _create_research_profiles():
        op.create_table(
            "research_profiles",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column(
                "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
            ),
            sa.Column("research_interests", sa.Text()),
            sa.Column("publications", sa.Text()),
            sa.Column("skills", sa.Text()),
            sa.Column("research_experience", sa.Text()),
            sa.Column("preferred_degree", sa.String(100)),
        )
        op.create_index("ix_research_profiles_user_id", "research_profiles", ["user_id"])

    create_if_missing("research_profiles", _create_research_profiles)

    def _create_cvs():
        op.create_table(
            "cvs",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column(
                "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
            ),
            sa.Column("file_url", sa.String(1000), nullable=False),
            sa.Column("version", sa.String(50)),
            sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_cvs_user_id", "cvs", ["user_id"])

    create_if_missing("cvs", _create_cvs)

    def _create_countries():
        op.create_table(
            "countries",
            sa.Column("country_code", sa.String(10), primary_key=True),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("study_information", sa.Text()),
            sa.Column("living_cost", sa.String(100)),
        )

    create_if_missing("countries", _create_countries)

    def _create_country_preferences():
        op.create_table(
            "country_preferences",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column(
                "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
            ),
            sa.Column(
                "country_code",
                sa.String(10),
                sa.ForeignKey("countries.country_code"),
                nullable=False,
            ),
            sa.Column("priority", sa.Integer()),
        )
        op.create_index("ix_country_preferences_user_id", "country_preferences", ["user_id"])
        op.create_index(
            "ix_country_preferences_country_code", "country_preferences", ["country_code"]
        )

    create_if_missing("country_preferences", _create_country_preferences)

    def _create_visa_information():
        op.create_table(
            "visa_information",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column(
                "country_code",
                sa.String(10),
                sa.ForeignKey("countries.country_code"),
                nullable=False,
            ),
            sa.Column("visa_type", sa.String(100)),
            sa.Column("requirements", sa.Text()),
            sa.Column("processing_time", sa.String(100)),
            sa.Column("last_updated", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_visa_information_country_code", "visa_information", ["country_code"])

    create_if_missing("visa_information", _create_visa_information)

    def _create_universities():
        op.create_table(
            "universities",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("name", sa.String(300), nullable=False),
            sa.Column(
                "country_code",
                sa.String(10),
                sa.ForeignKey("countries.country_code"),
                nullable=False,
            ),
            sa.Column("website", sa.String(500)),
            sa.Column("ranking", sa.String(100)),
            sa.Column("description", sa.Text()),
        )
        op.create_index("ix_universities_country_code", "universities", ["country_code"])

    create_if_missing("universities", _create_universities)

    def _create_departments():
        op.create_table(
            "departments",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column(
                "university_id",
                sa.Uuid(),
                sa.ForeignKey("universities.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("name", sa.String(300), nullable=False),
            sa.Column("description", sa.Text()),
        )
        op.create_index("ix_departments_university_id", "departments", ["university_id"])

    create_if_missing("departments", _create_departments)

    def _create_professors():
        op.create_table(
            "professors",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column(
                "university_id",
                sa.Uuid(),
                sa.ForeignKey("universities.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "department_id", sa.Uuid(), sa.ForeignKey("departments.id", ondelete="SET NULL")
            ),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("email", sa.String(320)),
            sa.Column("designation", sa.String(200)),
            sa.Column("research_areas", sa.Text()),
            sa.Column("profile_url", sa.String(500)),
        )
        op.create_index("ix_professors_university_id", "professors", ["university_id"])
        op.create_index("ix_professors_department_id", "professors", ["department_id"])

    create_if_missing("professors", _create_professors)

    def _create_course_programs():
        op.create_table(
            "course_programs",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column(
                "university_id",
                sa.Uuid(),
                sa.ForeignKey("universities.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("name", sa.String(300), nullable=False),
            sa.Column("degree_level", sa.String(100)),
            sa.Column("field_of_study", sa.String(200)),
            sa.Column("admission_requirements", sa.Text()),
            sa.Column("application_deadline", sa.Date()),
            sa.Column("application_url", sa.String(500)),
        )
        op.create_index("ix_course_programs_university_id", "course_programs", ["university_id"])

    create_if_missing("course_programs", _create_course_programs)

    def _create_fundings():
        op.create_table(
            "fundings",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column(
                "university_id", sa.Uuid(), sa.ForeignKey("universities.id", ondelete="SET NULL")
            ),
            sa.Column("title", sa.String(300), nullable=False),
            sa.Column("funding_type", sa.String(100)),
            sa.Column("eligibility", sa.Text()),
            sa.Column("amount", sa.String(100)),
            sa.Column("deadline", sa.Date()),
            sa.Column("application_url", sa.String(500)),
        )
        op.create_index("ix_fundings_university_id", "fundings", ["university_id"])

    create_if_missing("fundings", _create_fundings)

    def _create_match_results():
        op.create_table(
            "match_results",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column(
                "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
            ),
            sa.Column(
                "professor_id", sa.Uuid(), sa.ForeignKey("professors.id", ondelete="SET NULL")
            ),
            sa.Column(
                "university_id", sa.Uuid(), sa.ForeignKey("universities.id", ondelete="SET NULL")
            ),
            sa.Column(
                "course_program_id",
                sa.Uuid(),
                sa.ForeignKey("course_programs.id", ondelete="SET NULL"),
            ),
            sa.Column("funding_id", sa.Uuid(), sa.ForeignKey("fundings.id", ondelete="SET NULL")),
            sa.Column("match_score", sa.Float()),
            sa.Column("explanation", sa.Text()),
            sa.Column("status", sa.String(50)),
            sa.Column("algorithm_version", sa.String(50)),
            sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_match_results_user_id", "match_results", ["user_id"])

    create_if_missing("match_results", _create_match_results)

    def _create_professor_outreach():
        op.create_table(
            "professor_outreach",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column(
                "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
            ),
            sa.Column(
                "professor_id",
                sa.Uuid(),
                sa.ForeignKey("professors.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("funding_id", sa.Uuid(), sa.ForeignKey("fundings.id", ondelete="SET NULL")),
            sa.Column("purpose", sa.Text()),
            sa.Column("stage", sa.String(100)),
            sa.Column("planned_send_at", sa.DateTime(timezone=True)),
            sa.Column("sent_at", sa.DateTime(timezone=True)),
            sa.Column("follow_up_at", sa.DateTime(timezone=True)),
            sa.Column("response_status", sa.String(50)),
            sa.Column("outcome", sa.String(100)),
        )
        op.create_index("ix_professor_outreach_user_id", "professor_outreach", ["user_id"])
        op.create_index(
            "ix_professor_outreach_professor_id", "professor_outreach", ["professor_id"]
        )

    create_if_missing("professor_outreach", _create_professor_outreach)

    def _create_email_records():
        op.create_table(
            "email_records",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column(
                "outreach_id",
                sa.Uuid(),
                sa.ForeignKey("professor_outreach.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("subject", sa.String(500)),
            sa.Column("body", sa.Text()),
            sa.Column("direction", sa.String(20)),
            sa.Column("sent_at", sa.DateTime(timezone=True)),
            sa.Column("received_at", sa.DateTime(timezone=True)),
            sa.Column("response_summary", sa.Text()),
        )
        op.create_index("ix_email_records_outreach_id", "email_records", ["outreach_id"])

    create_if_missing("email_records", _create_email_records)

    def _create_professor_outreach_stage_history():
        op.create_table(
            "professor_outreach_stage_history",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column(
                "outreach_id",
                sa.Uuid(),
                sa.ForeignKey("professor_outreach.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("previous_stage", sa.String(100)),
            sa.Column("new_stage", sa.String(100)),
            sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("notes", sa.Text()),
        )
        op.create_index(
            "ix_professor_outreach_stage_history_outreach_id",
            "professor_outreach_stage_history",
            ["outreach_id"],
        )

    create_if_missing("professor_outreach_stage_history", _create_professor_outreach_stage_history)

    def _create_university_applications():
        op.create_table(
            "university_applications",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column(
                "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
            ),
            sa.Column(
                "university_id",
                sa.Uuid(),
                sa.ForeignKey("universities.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "course_program_id",
                sa.Uuid(),
                sa.ForeignKey("course_programs.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("application_type", sa.String(100)),
            sa.Column("stage", sa.String(100)),
            sa.Column("deadline", sa.Date()),
            sa.Column("submitted_at", sa.DateTime(timezone=True)),
            sa.Column("application_reference", sa.String(200)),
            sa.Column("decision", sa.String(100)),
        )
        op.create_index(
            "ix_university_applications_user_id", "university_applications", ["user_id"]
        )
        op.create_index(
            "ix_university_applications_university_id", "university_applications", ["university_id"]
        )
        op.create_index(
            "ix_university_applications_course_program_id",
            "university_applications",
            ["course_program_id"],
        )

    create_if_missing("university_applications", _create_university_applications)

    def _create_application_documents():
        op.create_table(
            "application_documents",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column(
                "university_application_id",
                sa.Uuid(),
                sa.ForeignKey("university_applications.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("document_type", sa.String(100)),
            sa.Column("file_url", sa.String(1000), nullable=False),
            sa.Column("status", sa.String(50)),
            sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index(
            "ix_application_documents_university_application_id",
            "application_documents",
            ["university_application_id"],
        )

    create_if_missing("application_documents", _create_application_documents)

    def _create_university_application_stage_history():
        op.create_table(
            "university_application_stage_history",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column(
                "application_id",
                sa.Uuid(),
                sa.ForeignKey("university_applications.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("previous_stage", sa.String(100)),
            sa.Column("new_stage", sa.String(100)),
            sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("notes", sa.Text()),
        )
        op.create_index(
            "ix_university_application_stage_history_application_id",
            "university_application_stage_history",
            ["application_id"],
        )

    create_if_missing(
        "university_application_stage_history", _create_university_application_stage_history
    )

    def _create_checklists():
        op.create_table(
            "checklists",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column(
                "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
            ),
            sa.Column(
                "professor_outreach_id",
                sa.Uuid(),
                sa.ForeignKey("professor_outreach.id", ondelete="CASCADE"),
            ),
            sa.Column(
                "university_application_id",
                sa.Uuid(),
                sa.ForeignKey("university_applications.id", ondelete="CASCADE"),
            ),
            sa.Column("title", sa.String(300)),
            sa.Column("checklist_type", sa.String(100)),
            sa.Column("status", sa.String(50)),
        )
        op.create_index("ix_checklists_user_id", "checklists", ["user_id"])

    create_if_missing("checklists", _create_checklists)

    def _create_checklist_items():
        op.create_table(
            "checklist_items",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column(
                "checklist_id",
                sa.Uuid(),
                sa.ForeignKey("checklists.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("title", sa.String(300), nullable=False),
            sa.Column("description", sa.Text()),
            sa.Column("status", sa.String(50)),
            sa.Column("due_date", sa.Date()),
            sa.Column("completed_at", sa.DateTime(timezone=True)),
            sa.Column("notes", sa.Text()),
        )
        op.create_index("ix_checklist_items_checklist_id", "checklist_items", ["checklist_id"])

    create_if_missing("checklist_items", _create_checklist_items)

    def _create_ai_application_strategies():
        op.create_table(
            "ai_application_strategies",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column(
                "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
            ),
            sa.Column("target_type", sa.String(50)),
            sa.Column(
                "outreach_id", sa.Uuid(), sa.ForeignKey("professor_outreach.id", ondelete="CASCADE")
            ),
            sa.Column(
                "application_id",
                sa.Uuid(),
                sa.ForeignKey("university_applications.id", ondelete="CASCADE"),
            ),
            sa.Column("strategy", sa.Text()),
            sa.Column("recommended_timeline", sa.Text()),
            sa.Column("model_version", sa.String(100)),
            sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index(
            "ix_ai_application_strategies_user_id", "ai_application_strategies", ["user_id"]
        )

    create_if_missing("ai_application_strategies", _create_ai_application_strategies)

    def _create_ai_recommendations():
        op.create_table(
            "ai_recommendations",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column(
                "strategy_id",
                sa.Uuid(),
                sa.ForeignKey("ai_application_strategies.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("recommendation_type", sa.String(100)),
            sa.Column("rationale", sa.Text()),
            sa.Column("priority", sa.String(50)),
            sa.Column("status", sa.String(50)),
        )
        op.create_index("ix_ai_recommendations_strategy_id", "ai_recommendations", ["strategy_id"])

    create_if_missing("ai_recommendations", _create_ai_recommendations)

    def _create_news():
        op.create_table(
            "news",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("title", sa.String(500), nullable=False),
            sa.Column("content", sa.Text()),
            sa.Column("source_url", sa.String(1000)),
            sa.Column("published_at", sa.DateTime(timezone=True)),
        )

    create_if_missing("news", _create_news)

    def _create_university_advertisements():
        op.create_table(
            "university_advertisements",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column(
                "university_id",
                sa.Uuid(),
                sa.ForeignKey("universities.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("title", sa.String(500), nullable=False),
            sa.Column("description", sa.Text()),
            sa.Column("target_url", sa.String(1000)),
            sa.Column("start_date", sa.Date()),
            sa.Column("end_date", sa.Date()),
        )
        op.create_index(
            "ix_university_advertisements_university_id",
            "university_advertisements",
            ["university_id"],
        )

    create_if_missing("university_advertisements", _create_university_advertisements)


def downgrade() -> None:
    pass
