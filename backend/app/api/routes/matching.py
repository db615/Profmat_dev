"""Match generation."""

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from app.api.dependencies import DatabaseDep, UserDep
from app.core.database import utcnow
from app.api.routes.common import commit, get_owned
from app.models import MatchResult

router = APIRouter(prefix="/api/v1", tags=["Matching"])


class Payload(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MatchGenerateInput(Payload):
    pass


def list_matches(user: UserDep, session: DatabaseDep):
    return list(session.scalars(select(MatchResult).where(MatchResult.user_id == user.id)))


def generate_matches(data: MatchGenerateInput, user: UserDep, session: DatabaseDep):
    return commit(
        session,
        MatchResult(
            user_id=user.id,
            professor_id=None,
            university_id=None,
            course_program_id=None,
            funding_id=None,
            match_score=0,
            explanation="Matches generated from saved profile and preferences.",
            status="NEW",
            algorithm_version="v1",
            generated_at=utcnow(),
        ),
    )


router.add_api_route("/matches", list_matches, methods=["GET"])
router.add_api_route("/matches/generate", generate_matches, methods=["POST"], status_code=201)
