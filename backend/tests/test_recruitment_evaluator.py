"""Tests for the AI recruitment evaluator's response validation and
failure handling. The OpenAI call is mocked at the `ask_for_json` level.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.ai.openai_client import AIServiceError
from app.ai.recruitment_evaluator import evaluate_application
from app.core.guild_config import GuildConfig

pytestmark = pytest.mark.asyncio

_VALID_RESPONSE = {
    "overall_score": 70,
    "activity_score": 65,
    "maturity_score": 72,
    "communication_score": 68,
    "teamwork_score": 74,
    "honesty_score": 70,
    "toxicity_risk_score": 80,
    "long_term_potential_score": 69,
    "explanation": "Reasonable applicant with average engagement signals.",
    "positives": ["Answered every question"],
    "concerns": ["Vague about past guild experience"],
    "recommendation": "interview",
}


@patch("app.ai.recruitment_evaluator.ask_for_json", new_callable=AsyncMock)
async def test_evaluate_application_returns_parsed_evaluation(mock_ask):
    mock_ask.return_value = _VALID_RESPONSE

    result = await evaluate_application(GuildConfig(), {"ign": "Test", "why_join": "Because"})

    assert result is not None
    assert result.overall_score == 70
    assert result.recommendation == "interview"


@patch("app.ai.recruitment_evaluator.ask_for_json", new_callable=AsyncMock)
async def test_evaluate_application_handles_malformed_schema(mock_ask):
    mock_ask.return_value = {"overall_score": "not-a-number"}  # invalid shape

    result = await evaluate_application(GuildConfig(), {"ign": "Test"})

    assert result is None  # degrades gracefully instead of raising


@patch("app.ai.recruitment_evaluator.ask_for_json", new_callable=AsyncMock)
async def test_evaluate_application_handles_ai_service_error(mock_ask):
    mock_ask.side_effect = AIServiceError("timeout")

    result = await evaluate_application(GuildConfig(), {"ign": "Test"})

    assert result is None
