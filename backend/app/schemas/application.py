"""
Pydantic schemas for the Application resource — the data contract between
the database models and the FastAPI routes / dashboard frontend.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.application import AIRecommendation, ApplicationDecision


class ApplicationSubmit(BaseModel):
    """Payload submitted by the Discord bot when an applicant finishes /apply."""

    discord_id: int
    discord_username: str
    answers: dict[str, str] = Field(
        ..., description="Mapping of question_id -> applicant's raw answer text"
    )


class AIEvaluationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ai_score: float | None
    ai_activity_score: float | None
    ai_maturity_score: float | None
    ai_communication_score: float | None
    ai_teamwork_score: float | None
    ai_honesty_score: float | None
    ai_toxicity_risk_score: float | None
    ai_long_term_potential_score: float | None
    ai_explanation: str | None
    ai_positives: list[str] | None
    ai_concerns: list[str] | None
    ai_recommendation: AIRecommendation | None
    ai_evaluated_at: datetime | None


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    member_id: int
    answers: dict
    submitted_at: datetime
    decision: ApplicationDecision
    decided_by_discord_id: int | None
    decided_at: datetime | None
    staff_notes: str | None

    ai_score: float | None
    ai_activity_score: float | None
    ai_maturity_score: float | None
    ai_communication_score: float | None
    ai_teamwork_score: float | None
    ai_honesty_score: float | None
    ai_toxicity_risk_score: float | None
    ai_long_term_potential_score: float | None
    ai_explanation: str | None
    ai_positives: list[str] | None
    ai_concerns: list[str] | None
    ai_recommendation: AIRecommendation | None
    ai_evaluated_at: datetime | None


class ApplicationDecisionUpdate(BaseModel):
    """Staff decision made via the dashboard or a Discord staff command."""

    decision: ApplicationDecision
    decided_by_discord_id: int
    staff_notes: str | None = None
