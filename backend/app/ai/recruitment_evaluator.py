"""
AI Recruitment Officer.

Takes an applicant's raw answers and produces a structured evaluation:
per-dimension scores (0-100), an overall score, a written explanation,
lists of positives/concerns, and a recommendation. This module NEVER
accepts or declines anyone — it only produces a recommendation that a
human reads and acts on (see app/services/recruitment_service.py and the
Discord /apply flow).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.ai.openai_client import AIServiceError, ask_for_json
from app.core.config import settings
from app.core.guild_config import GuildConfig
from app.core.logging import get_logger

logger = get_logger("guildos.ai")

_DIMENSIONS = [
    "activity",
    "maturity",
    "communication",
    "teamwork",
    "honesty",
    "toxicity_risk",
    "long_term_potential",
]


class RecruitmentEvaluation(BaseModel):
    """Validated shape of the AI's response. `toxicity_risk` is scored such
    that HIGH numbers mean LOW risk (i.e. it's a "safety" score), so that
    every dimension in the set follows the same "higher is better" convention
    and averages sensibly into an overall score.
    """

    overall_score: int = Field(ge=0, le=100)
    activity_score: int = Field(ge=0, le=100)
    maturity_score: int = Field(ge=0, le=100)
    communication_score: int = Field(ge=0, le=100)
    teamwork_score: int = Field(ge=0, le=100)
    honesty_score: int = Field(ge=0, le=100)
    toxicity_risk_score: int = Field(
        ge=0, le=100, description="100 = no toxicity risk detected, 0 = severe risk"
    )
    long_term_potential_score: int = Field(ge=0, le=100)
    explanation: str
    positives: list[str]
    concerns: list[str]
    recommendation: str  # "accept" | "interview" | "decline"


def _build_system_prompt(guild_config: GuildConfig) -> str:
    return f"""{guild_config.ai_personality}

You are evaluating a membership application. You must respond with a single
JSON object and nothing else, matching exactly this schema:

{{
  "overall_score": <int 0-100>,
  "activity_score": <int 0-100>,
  "maturity_score": <int 0-100>,
  "communication_score": <int 0-100>,
  "teamwork_score": <int 0-100>,
  "honesty_score": <int 0-100>,
  "toxicity_risk_score": <int 0-100, where 100 means NO toxicity risk and 0 means SEVERE risk>,
  "long_term_potential_score": <int 0-100>,
  "explanation": "<2-4 sentence explanation of your overall reasoning>",
  "positives": ["<short bullet>", ...],
  "concerns": ["<short bullet>", ...],
  "recommendation": "<one of: accept, interview, decline>"
}}

Scoring guidance:
- activity: does their stated playtime/availability suggest they'll actually
  be around and engaged?
- maturity: tone, self-awareness, how they write about conflict or past issues.
- communication: clarity, effort, coherence of their answers.
- teamwork: evidence of collaborative behavior, not just solo achievements.
- honesty: internal consistency; vague or contradictory answers should lower this.
- toxicity_risk_score: look for hostility, entitlement, blame-shifting, or
  red flags in how they describe past conflicts or guilds they left. Remember
  high = safe, low = risky.
- long_term_potential: likelihood they stick around and grow into a valuable,
  possibly future-staff member, based on everything above.
- recommendation must reflect the overall picture, not just the overall_score
  number — e.g. a high score with one serious toxicity red flag should
  usually be "interview", not "accept".

Never fabricate information not present in the answers. If an answer is
missing, thin, or evasive, treat that as a legitimate signal (usually
lowering communication/honesty) rather than assuming the best about the
applicant. Be specific in `positives` and `concerns` — reference what they
actually said, not generic statements."""


def _build_user_prompt(guild_config: GuildConfig, answers: dict[str, str]) -> str:
    lines = ["Applicant answers:\n"]
    question_lookup = {q["id"]: q["question"] for q in guild_config.application_questions}
    for question_id, answer in answers.items():
        question_text = question_lookup.get(question_id, question_id)
        lines.append(f"Q: {question_text}\nA: {answer.strip() or '(no answer given)'}\n")
    return "\n".join(lines)


async def evaluate_application(
    guild_config: GuildConfig, answers: dict[str, str]
) -> RecruitmentEvaluation | None:
    """Run the AI evaluation for one application.

    Returns None (rather than raising) on AI failure so the calling service
    can fall back to flagging the application for manual review instead of
    crashing the whole submission flow — an applicant should never be lost
    because the AI call failed.
    """
    system_prompt = _build_system_prompt(guild_config)
    user_prompt = _build_user_prompt(guild_config, answers)

    try:
        raw = await ask_for_json(system_prompt, user_prompt)
    except AIServiceError as exc:
        logger.error("Recruitment evaluation failed (AI service error): %s", exc)
        return None

    try:
        evaluation = RecruitmentEvaluation.model_validate(raw)
    except ValidationError as exc:
        logger.error("Recruitment evaluation failed (bad schema from model): %s | raw=%s", exc, raw)
        return None

    logger.info(
        "Recruitment evaluation complete: overall=%s recommendation=%s",
        evaluation.overall_score,
        evaluation.recommendation,
    )
    return evaluation
