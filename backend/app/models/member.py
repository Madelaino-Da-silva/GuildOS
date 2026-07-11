"""
Member model.

Represents a person tracked by GuildOS — whether a full guild member,
a former member, or (via the linked Application) a prospective recruit.
This is the central entity that the Community Manager, Promotion
Assistant, and Moderator Assistant features will all attach data to.
"""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MemberStatus(str, enum.Enum):
    APPLICANT = "applicant"
    ACTIVE = "active"
    INACTIVE = "inactive"
    STAFF = "staff"
    LEFT = "left"
    BANNED = "banned"


class Member(Base):
    __tablename__ = "members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    discord_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    discord_username: Mapped[str] = mapped_column(String(128), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(128), nullable=True)

    status: Mapped[MemberStatus] = mapped_column(
        Enum(MemberStatus), default=MemberStatus.APPLICANT, nullable=False
    )
    rank: Mapped[str | None] = mapped_column(String(64), nullable=True)

    join_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    left_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Rolling activity counters. Updated by the Community Manager /
    # activity-tracking service, not computed live from Discord each time.
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    voice_minutes: Mapped[int] = mapped_column(Integer, default=0)
    events_attended: Mapped[int] = mapped_column(Integer, default=0)
    warnings: Mapped[int] = mapped_column(Integer, default=0)
    recruitments_made: Mapped[int] = mapped_column(Integer, default=0)

    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    applications: Mapped[list["Application"]] = relationship(
        "Application", back_populates="member", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover - debug convenience
        return f"<Member id={self.id} discord_id={self.discord_id} status={self.status}>"
