"""Professor match generation.

The current implementation is a deterministic, dependency-free keyword matcher
(``basic-v1``). It is intentionally a seam: the CV-based semantic matcher from
``resume_matcher`` can replace ``_rank`` later without changing the API.
"""

import re

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict
from sqlalchemy import delete, select

from app.api.dependencies import DatabaseDep, UserDep
from app.core.database import utcnow
from app.models import (
    CountryPreference,
    MatchResult,
    Professor,
    ResearchProfile,
    University,
)
from app.schemas.profmat import MatchResultRead

router = APIRouter(tags=["Matching"])

MAX_MATCHES = 20
ALGORITHM_VERSION = "basic-v1"
_WORD = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "and",
    "the",
    "for",
    "with",
    "from",
    "that",
    "this",
    "their",
    "your",
    "have",
    "has",
    "using",
    "based",
    "research",
    "professor",
    "university",
    "student",
    "study",
    "studies",
}


class Payload(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MatchGenerateInput(Payload):
    pass


def _tokens(text: str | None) -> set[str]:
    return {
        word
        for word in _WORD.findall((text or "").lower())
        if len(word) > 2 and word not in _STOPWORDS
    }


def _keyword_score(interests: set[str], professor: Professor) -> tuple[float, list[str]]:
    if not interests:
        return 0.0, []
    profile = _tokens(professor.research_areas) | _tokens(professor.name)
    overlap = sorted(interests & profile)
    if not overlap:
        return 0.0, []
    return round(len(overlap) / len(interests), 4), overlap


def list_matches(user: UserDep, session: DatabaseDep) -> list[MatchResultRead]:
    return list(
        session.scalars(
            select(MatchResult)
            .where(MatchResult.user_id == user.id)
            .order_by(MatchResult.match_score.desc(), MatchResult.generated_at.desc())
        )
    )


def generate_matches(
    data: MatchGenerateInput, user: UserDep, session: DatabaseDep
) -> list[MatchResultRead]:
    session.execute(delete(MatchResult).where(MatchResult.user_id == user.id))

    research = session.scalars(
        select(ResearchProfile).where(ResearchProfile.user_id == user.id)
    ).first()
    interests = _tokens(research.research_interests if research else None) | _tokens(
        research.skills if research else None
    )
    preferred = {
        preference.country_code
        for preference in session.scalars(
            select(CountryPreference).where(CountryPreference.user_id == user.id)
        )
    }

    rows = session.execute(
        select(Professor, University).join(University, Professor.university_id == University.id)
    ).all()

    ranked: list[tuple[float, str, Professor, str]] = []
    for professor, university in rows:
        score, overlap = _keyword_score(interests, professor)
        in_preferred = university.country_code in preferred
        if in_preferred:
            score = round(min(1.0, score + 0.1), 4)
        reasons = []
        if overlap:
            reasons.append("research keywords: " + ", ".join(overlap[:6]))
        if in_preferred:
            reasons.append(f"preferred country ({university.country_code})")
        explanation = (
            "Matched on " + "; ".join(reasons) + "."
            if reasons
            else "Suggested from the available professor catalog."
        )
        ranked.append((score, professor.name, professor, explanation))

    ranked.sort(key=lambda item: (-item[0], item[1]))

    created = [
        MatchResult(
            user_id=user.id,
            professor_id=professor.id,
            match_score=score,
            explanation=explanation,
            status="NEW",
            algorithm_version=ALGORITHM_VERSION,
            generated_at=utcnow(),
        )
        for score, _, professor, explanation in ranked[:MAX_MATCHES]
    ]
    if created:
        session.add_all(created)
    session.commit()
    for match in created:
        session.refresh(match)
    return created


router.add_api_route(
    "/matches", list_matches, methods=["GET"], response_model=list[MatchResultRead]
)
router.add_api_route(
    "/matches/generate",
    generate_matches,
    methods=["POST"],
    status_code=201,
    response_model=list[MatchResultRead],
)
