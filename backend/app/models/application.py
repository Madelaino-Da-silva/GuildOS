"""
Application model.

Stores a single guild membership application: the applicant's raw answers,
the AI's structured evaluation of those answers, and the eventual staff
decision. Nothing here ever auto-accepts or auto-rejects a member — the
`decision` field starts as PENDING and is only ever changed by a human
via the dashboard or a Discord staff command.
"""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ApplicationDecision(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    INTERVIEW = "interview"
    DECLINED = "declined"


class AIRecommendation(str, enum.Enum):
    ACCEPT = "accept"
    INTERVIEW = "interview"
    DECLINE = "decline"


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"), nullable=False)

    # Raw applicant answers, keyed by question ID as configured in Settings.
    # Stored as JSON so the question set can change over time without
    # requiring a schema migration for every new/removed question.
    answers: Mapped[dict] = mapped_column(JSON, nullable=False)

    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # ---- AI evaluation --------------------------------------------------
    ai_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_activity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_maturity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_communication_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_teamwork_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_honesty_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_toxicity_risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_long_term_potential_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    ai_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_positives: Mapped[list | None] = mapped_column(JSON, nullable=True)
    ai_concerns: Mapped[list | None] = mapped_column(JSON, nullable=True)
    ai_recommendation: Mapped[AIRecommendation | None] = mapped_column(
        Enum(AIRecommendation), nullable=True
    )
    ai_evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ai_model_used: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ai_raw_response: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # ---- Human decision --------------------------------------------------
    decision: Mapped[ApplicationDecision] = mapped_column(
        Enum(ApplicationDecision), default=ApplicationDecision.PENDING, nullable=False
    )
    decided_by_discord_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    staff_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    member: Mapped["Member"] = relationship("Member", back_populates="applications")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Application id={self.id} member_id={self.member_id} decision={self.decision}>"
