from datetime import UTC, datetime

from sqlalchemy import DateTime, Engine, create_engine
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.types import TypeDecorator


def create_database_engine(database_url: str) -> Engine:
    return create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 5},
        isolation_level="READ COMMITTED",
    )


def utcnow() -> datetime:
    return datetime.now(UTC)


class UTCDateTime(TypeDecorator[datetime]):
    impl = DateTime(timezone=True).with_variant(DATETIME(fsp=6), "mysql", "mariadb")
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None and value.tzinfo is not None:
            return value.astimezone(UTC).replace(tzinfo=None)
        return value

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value


class Base(DeclarativeBase):
    pass
