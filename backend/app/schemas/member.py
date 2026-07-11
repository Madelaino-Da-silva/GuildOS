"""Pydantic schemas for the Member resource."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.member import MemberStatus


class MemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    discord_id: int
    discord_username: str
    display_name: str | None
    status: MemberStatus
    rank: str | None
    join_date: datetime | None
    message_count: int
    voice_minutes: int
    events_attended: int
    warnings: int
    recruitments_made: int
    last_active_at: datetime | None
