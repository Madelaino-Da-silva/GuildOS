"""
Guild-specific configuration that staff can edit through the dashboard
Settings page — as opposed to `config.py`, which holds infrastructure
settings (secrets, DB URL) that only change via environment variables.

For this first build phase this is backed by a single JSON file on disk
(`data/guild_config.json`) so it works with zero extra infrastructure.
The Settings API routes (added when the Dashboard feature is built) will
read and write through this same module, and it's structured so it can be
swapped for a database-backed table later without touching callers.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

_CONFIG_PATH = Path("data/guild_config.json")

DEFAULT_APPLICATION_QUESTIONS: list[dict[str, str]] = [
    {"id": "ign", "question": "What is your Minecraft in-game name?"},
    {"id": "age", "question": "How old are you? (Guild minimum age applies)"},
    {"id": "playtime", "question": "How many hours per week do you typically play?"},
    {"id": "timezone", "question": "What timezone are you in?"},
    {"id": "experience", "question": "What guilds/servers have you been part of before, and why did you leave?"},
    {"id": "why_join", "question": "Why do you want to join Outsiders specifically?"},
    {"id": "contribution", "question": "What can you contribute to the guild (PvP, building, redstone, farming, community, etc.)?"},
    {"id": "conflict", "question": "Describe how you'd handle a disagreement with another guild member."},
    {"id": "rules_ack", "question": "Have you read and do you agree to the guild rules? Any questions about them?"},
]

DEFAULT_AI_PERSONALITY = (
    "You are a fair, experienced guild recruitment officer for a Minecraft "
    "guild called Outsiders on the BendersMC server. You are thoughtful, "
    "direct, and slightly informal in tone, but always professional and "
    "fair. You never let a single red flag override an otherwise strong "
    "application without explaining the trade-off, and you never let a "
    "single strong answer paper over a genuine concern. You are honest "
    "about uncertainty."
)


class GuildConfig(BaseModel):
    application_questions: list[dict[str, str]] = Field(
        default_factory=lambda: DEFAULT_APPLICATION_QUESTIONS
    )
    ai_personality: str = DEFAULT_AI_PERSONALITY
    minimum_age: int = 13
    report_channel_id: int | None = None
    staff_channel_id: int | None = None
    application_channel_id: int | None = None
    dm_reports_to_owner: bool = True
    promotion_rules: dict[str, Any] = Field(default_factory=dict)
    event_frequency_days: int = 7


def load_guild_config() -> GuildConfig:
    if _CONFIG_PATH.exists():
        data = json.loads(_CONFIG_PATH.read_text())
        return GuildConfig(**data)
    return GuildConfig()


def save_guild_config(config: GuildConfig) -> None:
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CONFIG_PATH.write_text(config.model_dump_json(indent=2))
