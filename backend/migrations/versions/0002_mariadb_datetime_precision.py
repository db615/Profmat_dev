"""Preserve microsecond precision for MariaDB auth timestamps."""

from alembic import op
from sqlalchemy.dialects.mysql import DATETIME

revision = "0002_mariadb_datetime_precision"
down_revision = "0001_auth"
branch_labels = None
depends_on = None

TIMESTAMP_COLUMNS = {
    "users": [("created_at", False)],
    "refresh_sessions": [
        ("expires_at", False),
        ("created_at", False),
        ("used_at", True),
        ("revoked_at", True),
    ],
    "google_challenges": [("expires_at", False)],
    "auth_rate_limits": [("expires_at", False)],
}


def set_precision(precision: int) -> None:
    if op.get_bind().dialect.name not in {"mysql", "mariadb"}:
        return
    for table_name, columns in TIMESTAMP_COLUMNS.items():
        for column_name, nullable in columns:
            op.alter_column(
                table_name,
                column_name,
                type_=DATETIME(fsp=precision),
                existing_type=DATETIME(),
                existing_nullable=nullable,
            )


def upgrade() -> None:
    set_precision(6)


def downgrade() -> None:
    set_precision(0)
