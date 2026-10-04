from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from search_prof.backend.app.core.database import utcnow
from search_prof.backend.app.models import AuthRateLimit, GoogleChallenge, RefreshSession, User


class AuthRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def user_by_email(self, email: str) -> User | None:
        return self.session.scalar(select(User).where(User.email == email))

    def user_by_google_sub(self, google_sub: str) -> User | None:
        return self.session.scalar(select(User).where(User.google_sub == google_sub))

    def lock_user(self, user_id: UUID) -> User | None:
        return self.session.scalar(
            select(User)
            .where(User.id == user_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    def refresh_by_hash(self, token_hash: str) -> RefreshSession | None:
        return self.session.scalar(
            select(RefreshSession)
            .where(RefreshSession.token_hash == token_hash)
            .execution_options(populate_existing=True)
        )

    def revoke_family(self, family_id: UUID) -> None:
        self.session.execute(
            update(RefreshSession)
            .where(RefreshSession.family_id == family_id, RefreshSession.revoked_at.is_(None))
            .values(revoked_at=utcnow())
        )

    def revoke_all(self, user_id: UUID) -> None:
        self.session.execute(
            update(RefreshSession)
            .where(RefreshSession.user_id == user_id, RefreshSession.revoked_at.is_(None))
            .values(revoked_at=utcnow())
        )

    def consume_google_challenge(self, token_hash: str) -> GoogleChallenge | None:
        challenge = self.session.scalar(
            select(GoogleChallenge)
            .where(GoogleChallenge.token_hash == token_hash)
            .with_for_update()
        )
        if challenge:
            self.session.delete(challenge)
            self.session.commit()
        return challenge

    def hit_rate_limit(self, bucket_hash: str, expires_at: datetime) -> int:
        if self.session.get_bind().dialect.name == "sqlite":
            statement = (
                sqlite_insert(AuthRateLimit)
                .values(bucket_hash=bucket_hash, attempts=1, expires_at=expires_at)
                .on_conflict_do_update(
                    index_elements=[AuthRateLimit.bucket_hash],
                    set_={"attempts": AuthRateLimit.attempts + 1},
                )
                .returning(AuthRateLimit.attempts)
            )
            attempts = self.session.execute(statement).scalar_one()
        else:
            self.session.execute(
                mysql_insert(AuthRateLimit)
                .values(bucket_hash=bucket_hash, attempts=1, expires_at=expires_at)
                .on_duplicate_key_update(attempts=AuthRateLimit.attempts + 1)
            )
            attempts = self.session.execute(
                select(AuthRateLimit.attempts).where(AuthRateLimit.bucket_hash == bucket_hash)
            ).scalar_one()
        self.session.commit()
        return attempts
