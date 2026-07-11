"""
Recruitment service.

This is the orchestration layer between the Discord bot / API routes and
the lower-level AI + database layers. It's responsible for:

  1. Finding-or-creating the Member record for an applicant.
  2. Persisting the Application with their raw answers.
  3. Running the AI evaluation and saving the results.
  4. Building a human-readable report ready to post to Discord or the
     dashboard.

Kept free of any Discord-specific or FastAPI-specific code so it can be
called from either the bot or the HTTP API without duplication.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.recruitment_evaluator import RecruitmentEvaluation, evaluate_application
from app.core.guild_config import load_guild_config
from app.core.logging import get_logger
from app.models.application import AIRecommendation, Application, ApplicationDecision
from app.models.member import Member, MemberStatus

logger = get_logger("guildos.recruitment")


async def get_or_create_member(
    db: AsyncSession, discord_id: int, discord_username: str
) -> Member:
    result = await db.execute(select(Member).where(Member.discord_id == discord_id))
    member = result.scalar_one_or_none()
    if member is not None:
        return member

    member = Member(
        discord_id=discord_id,
        discord_username=discord_username,
        status=MemberStatus.APPLICANT,
    )
    db.add(member)
    await db.flush()  # populate member.id without committing yet
    return member


async def submit_application(
    db: AsyncSession, discord_id: int, discord_username: str, answers: dict[str, str]
) -> Application:
    """Create the Application record, run the AI evaluation, and persist
    the result. Returns the fully-evaluated Application (evaluation fields
    will be None if the AI call failed — the application itself is never
    lost, only its scoring is deferred/marked for manual review).
    """
    member = await get_or_create_member(db, discord_id, discord_username)

    application = Application(member_id=member.id, answers=answers)
    # Assign the relationship directly (not just member_id) since we already
    # hold `member` in memory. This avoids a lazy-load of `application.member`
    # later, which would raise MissingGreenlet under AsyncSession — relationship
    # attributes aren't implicitly awaitable, so callers must either eager-load
    # via selectinload() or, as here, already have the related object attached.
    application.member = member
    db.add(application)
    await db.flush()

    guild_config = load_guild_config()
    evaluation = await evaluate_application(guild_config, answers)

    if evaluation is not None:
        _apply_evaluation_to_application(application, evaluation)
    else:
        logger.warning(
            "AI evaluation unavailable for application %s — leaving for manual review",
            application.id,
        )

    await db.commit()
    await db.refresh(application)
    return application


def _apply_evaluation_to_application(
    application: Application, evaluation: RecruitmentEvaluation
) -> None:
    application.ai_score = evaluation.overall_score
    application.ai_activity_score = evaluation.activity_score
    application.ai_maturity_score = evaluation.maturity_score
    application.ai_communication_score = evaluation.communication_score
    application.ai_teamwork_score = evaluation.teamwork_score
    application.ai_honesty_score = evaluation.honesty_score
    application.ai_toxicity_risk_score = evaluation.toxicity_risk_score
    application.ai_long_term_potential_score = evaluation.long_term_potential_score
    application.ai_explanation = evaluation.explanation
    application.ai_positives = evaluation.positives
    application.ai_concerns = evaluation.concerns

    try:
        application.ai_recommendation = AIRecommendation(evaluation.recommendation.lower())
    except ValueError:
        logger.warning("Unrecognized AI recommendation value: %s", evaluation.recommendation)
        application.ai_recommendation = None

    application.ai_evaluated_at = datetime.now(timezone.utc)


async def record_staff_decision(
    db: AsyncSession,
    application: Application,
    decision: ApplicationDecision,
    decided_by_discord_id: int,
    staff_notes: str | None = None,
) -> Application:
    """The ONLY place an application's decision is ever set. Always driven
    by an explicit human action (dashboard click or Discord staff command),
    never by the AI directly.
    """
    application.decision = decision
    application.decided_by_discord_id = decided_by_discord_id
    application.decided_at = datetime.now(timezone.utc)
    application.staff_notes = staff_notes

    if decision == ApplicationDecision.ACCEPTED:
        member_result = application.member  # relationship already loaded in most call sites
        if member_result is not None:
            member_result.status = MemberStatus.ACTIVE
            member_result.join_date = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(application)
    return application


def format_discord_report(application: Application, member: Member) -> str:
    """Build the professional Discord embed-style report text for a
    freshly-evaluated application. Returned as plain text here; the
    Discord cog wraps this into a `discord.Embed`.
    """
    if application.ai_score is None:
        return (
            f"⚠️ **Application from {member.discord_username} could not be auto-evaluated.**\n"
            f"The AI service failed — please review this application manually.\n"
            f"Application ID: `{application.id}`"
        )

    rec_emoji = {
        AIRecommendation.ACCEPT: "✅",
        AIRecommendation.INTERVIEW: "🟡",
        AIRecommendation.DECLINE: "🔴",
    }.get(application.ai_recommendation, "❔")

    positives = "\n".join(f"• {p}" for p in (application.ai_positives or [])) or "• None noted"
    concerns = "\n".join(f"• {c}" for c in (application.ai_concerns or [])) or "• None noted"

    return (
        f"## New Application — {member.discord_username}\n"
        f"**Overall Score:** {application.ai_score}/100\n"
        f"**AI Recommendation:** {rec_emoji} {application.ai_recommendation.value.upper() if application.ai_recommendation else 'UNKNOWN'}\n\n"
        f"**Dimension Scores**\n"
        f"Activity: {application.ai_activity_score} · "
        f"Maturity: {application.ai_maturity_score} · "
        f"Communication: {application.ai_communication_score}\n"
        f"Teamwork: {application.ai_teamwork_score} · "
        f"Honesty: {application.ai_honesty_score} · "
        f"Toxicity Risk (higher=safer): {application.ai_toxicity_risk_score} · "
        f"Long-term Potential: {application.ai_long_term_potential_score}\n\n"
        f"**Why:** {application.ai_explanation}\n\n"
        f"**Positives**\n{positives}\n\n"
        f"**Concerns**\n{concerns}\n\n"
        f"_This is a recommendation only — a staff member must accept, interview, "
        f"or decline this applicant using `/recruit review {application.id}`._"
    )
