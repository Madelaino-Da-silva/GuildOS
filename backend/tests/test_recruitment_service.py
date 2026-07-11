"""Tests for the recruitment service — the core of the AI Recruitment
Officer feature. The AI call itself is mocked so tests are fast, free,
and deterministic; `test_recruitment_evaluator.py` covers prompt/schema
behavior separately.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.ai.recruitment_evaluator import RecruitmentEvaluation
from app.core.guild_config import GuildConfig
from app.models.application import ApplicationDecision
from app.models.member import MemberStatus
from app.services.recruitment_service import (
    get_or_create_member,
    record_staff_decision,
    submit_application,
)

pytestmark = pytest.mark.asyncio

_FAKE_EVALUATION = RecruitmentEvaluation(
    overall_score=82,
    activity_score=90,
    maturity_score=85,
    communication_score=80,
    teamwork_score=75,
    honesty_score=88,
    toxicity_risk_score=95,
    long_term_potential_score=78,
    explanation="Strong, consistent answers with good self-awareness.",
    positives=["Plays 20+ hours/week", "Clear communicator"],
    concerns=["Limited PvP experience"],
    recommendation="accept",
)


async def test_get_or_create_member_is_idempotent(db_session):
    member1 = await get_or_create_member(db_session, discord_id=111, discord_username="Steve")
    await db_session.commit()
    member2 = await get_or_create_member(db_session, discord_id=111, discord_username="Steve")

    assert member1.id == member2.id
    assert member1.status == MemberStatus.APPLICANT


@patch("app.services.recruitment_service.evaluate_application", new_callable=AsyncMock)
async def test_submit_application_persists_ai_evaluation(mock_evaluate, db_session):
    mock_evaluate.return_value = _FAKE_EVALUATION

    application = await submit_application(
        db_session,
        discord_id=222,
        discord_username="Alex",
        answers={"ign": "AlexMC", "why_join": "Love the community"},
    )

    assert application.ai_score == 82
    assert application.ai_recommendation.value == "accept"
    assert application.ai_toxicity_risk_score == 95
    assert "Clear communicator" in application.ai_positives
    assert application.decision == ApplicationDecision.PENDING  # never auto-decided


@patch("app.services.recruitment_service.evaluate_application", new_callable=AsyncMock)
async def test_submit_application_survives_ai_failure(mock_evaluate, db_session):
    """If the AI service fails, the application must still be saved --
    an applicant should never be lost due to an AI outage.
    """
    mock_evaluate.return_value = None

    application = await submit_application(
        db_session, discord_id=333, discord_username="Jordan", answers={"ign": "JordanMC"}
    )

    assert application.id is not None
    assert application.ai_score is None
    assert application.decision == ApplicationDecision.PENDING


@patch("app.services.recruitment_service.evaluate_application", new_callable=AsyncMock)
async def test_staff_decision_never_set_by_ai(mock_evaluate, db_session):
    mock_evaluate.return_value = _FAKE_EVALUATION

    application = await submit_application(
        db_session, discord_id=444, discord_username="Sam", answers={"ign": "SamMC"}
    )
    # Even though the AI recommended "accept", decision remains pending
    # until a human calls record_staff_decision explicitly.
    assert application.decision == ApplicationDecision.PENDING

    await db_session.refresh(application, attribute_names=["member"])
    updated = await record_staff_decision(
        db_session,
        application,
        decision=ApplicationDecision.ACCEPTED,
        decided_by_discord_id=999,
        staff_notes="Great fit, welcomed by officer team.",
    )

    assert updated.decision == ApplicationDecision.ACCEPTED
    assert updated.decided_by_discord_id == 999
    assert updated.member.status == MemberStatus.ACTIVE
