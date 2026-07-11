"""
Recruitment cog: implements the `/apply` slash command as a multi-step
Discord modal workflow, runs the AI evaluation, and posts a report to the
configured staff/report channel (and optionally DMs the guild owner).

Discord modals are limited to 5 input fields each, so applications with
more than 5 questions are split across sequential modals connected by a
"Continue" button. Partial answers are held in memory per-user for the
duration of the flow (a user mid-application isn't persisted to the DB
until they finish, so an abandoned application never pollutes the data).

Staff never see an auto-decision — only `/recruit review` (or the
dashboard) can accept/interview/decline, and that always requires an
explicit staff member's action.
"""
from __future__ import annotations

from typing import Any

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import session_scope
from app.core.guild_config import load_guild_config
from app.core.logging import get_logger
from app.models.application import Application, ApplicationDecision
from app.services.recruitment_service import (
    format_discord_report,
    record_staff_decision,
    submit_application,
)

logger = get_logger("guildos.bot.recruitment")

_QUESTIONS_PER_MODAL = 5

# In-memory holding area for in-progress multi-step applications.
# Key: discord user ID. Cleared as soon as the applicant finishes or the
# bot restarts (an interrupted application simply has to be restarted,
# which is an acceptable trade-off for the simplicity of not persisting
# half-finished, unvalidated form data).
_pending_answers: dict[int, dict[str, str]] = {}


def _chunk_questions(questions: list[dict[str, str]]) -> list[list[dict[str, str]]]:
    return [
        questions[i : i + _QUESTIONS_PER_MODAL]
        for i in range(0, len(questions), _QUESTIONS_PER_MODAL)
    ]


class ApplicationStepModal(discord.ui.Modal):
    """One page of the application. `step_index` tracks which chunk of
    questions this modal covers so we know whether to show a "Continue"
    button or submit for real afterward.
    """

    def __init__(self, questions_chunks: list[list[dict[str, str]]], step_index: int):
        chunk = questions_chunks[step_index]
        is_last_step = step_index == len(questions_chunks) - 1
        title = f"Outsiders Application (Part {step_index + 1}/{len(questions_chunks)})"
        super().__init__(title=title[:45])

        self.questions_chunks = questions_chunks
        self.step_index = step_index
        self.is_last_step = is_last_step
        self.fields: list[discord.ui.TextInput] = []

        for question in chunk:
            text_input = discord.ui.TextInput(
                label=question["question"][:45],
                style=discord.TextStyle.paragraph,
                required=True,
                max_length=1000,
            )
            self.add_item(text_input)
            self.fields.append((question["id"], text_input))  # type: ignore[arg-type]

    async def on_submit(self, interaction: discord.Interaction) -> None:
        user_id = interaction.user.id
        _pending_answers.setdefault(user_id, {})
        for question_id, text_input in self.fields:
            _pending_answers[user_id][question_id] = str(text_input.value)

        if self.is_last_step:
            await interaction.response.defer(ephemeral=True, thinking=True)
            await _finalize_application(interaction)
        else:
            view = ContinueApplicationView(self.questions_chunks, self.step_index + 1)
            await interaction.response.send_message(
                "Got it — click **Continue** to answer the next section.",
                view=view,
                ephemeral=True,
            )


class ContinueApplicationView(discord.ui.View):
    def __init__(self, questions_chunks: list[list[dict[str, str]]], next_step: int):
        super().__init__(timeout=900)  # 15 minutes to continue
        self.questions_chunks = questions_chunks
        self.next_step = next_step

    @discord.ui.button(label="Continue", style=discord.ButtonStyle.primary, emoji="➡️")
    async def continue_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = ApplicationStepModal(self.questions_chunks, self.next_step)
        await interaction.response.send_modal(modal)


class StartApplicationView(discord.ui.View):
    def __init__(self, questions_chunks: list[list[dict[str, str]]]):
        super().__init__(timeout=900)
        self.questions_chunks = questions_chunks

    @discord.ui.button(label="Start Application", style=discord.ButtonStyle.success, emoji="📝")
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        _pending_answers.pop(interaction.user.id, None)  # fresh start
        modal = ApplicationStepModal(self.questions_chunks, 0)
        await interaction.response.send_modal(modal)


async def _finalize_application(interaction: discord.Interaction) -> None:
    """Persist the completed application, run the AI evaluation, and post
    the report. Called after the last modal step is submitted.
    """
    user = interaction.user
    answers = _pending_answers.pop(user.id, {})
    guild_config = load_guild_config()

    async with session_scope() as db:
        application = await submit_application(
            db,
            discord_id=user.id,
            discord_username=str(user),
            answers=answers,
        )
        member = application.member  # populated by relationship load in submit_application's flush

        report_text = format_discord_report(application, member)

    await interaction.followup.send(
        "✅ Your application has been submitted! Staff will review it and follow up with you.",
        ephemeral=True,
    )

    # Post the report to the configured report/staff channel.
    channel_id = guild_config.application_channel_id or settings.DISCORD_APPLICATION_CHANNEL_ID
    if channel_id:
        channel = interaction.client.get_channel(channel_id)
        if channel is not None:
            await channel.send(report_text)
        else:
            logger.warning("Configured application channel %s not found/accessible", channel_id)
    else:
        logger.warning("No application channel configured — report not posted anywhere")

    # Optionally DM the guild owner.
    if guild_config.dm_reports_to_owner and settings.DISCORD_OWNER_DM_USER_ID:
        try:
            owner = await interaction.client.fetch_user(settings.DISCORD_OWNER_DM_USER_ID)
            await owner.send(f"📩 New application received:\n\n{report_text}")
        except discord.HTTPException as exc:
            logger.warning("Failed to DM owner about new application: %s", exc)


class RecruitmentCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="apply", description="Apply to join Outsiders")
    async def apply(self, interaction: discord.Interaction) -> None:
        guild_config = load_guild_config()
        chunks = _chunk_questions(guild_config.application_questions)
        view = StartApplicationView(chunks)
        await interaction.response.send_message(
            "Thanks for your interest in **Outsiders**! Click below to start your application. "
            f"It's split into {len(chunks)} short section(s) — answer honestly, our recruitment "
            "process is reviewed by both AI and real staff.",
            view=view,
            ephemeral=True,
        )

    recruit_group = app_commands.Group(name="recruit", description="Recruitment staff commands")

    @recruit_group.command(name="review", description="Review and decide on an application")
    @app_commands.describe(application_id="The application ID to review", decision="accept, interview, or decline")
    @app_commands.choices(
        decision=[
            app_commands.Choice(name="Accept", value="accepted"),
            app_commands.Choice(name="Interview", value="interview"),
            app_commands.Choice(name="Decline", value="declined"),
        ]
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def review(
        self,
        interaction: discord.Interaction,
        application_id: int,
        decision: app_commands.Choice[str],
        notes: str | None = None,
    ) -> None:
        async with session_scope() as db:
            result = await db.execute(
                select(Application)
                .options(selectinload(Application.member))
                .where(Application.id == application_id)
            )
            application = result.scalar_one_or_none()
            if application is None:
                await interaction.response.send_message(
                    f"No application found with ID `{application_id}`.", ephemeral=True
                )
                return

            await record_staff_decision(
                db,
                application,
                decision=ApplicationDecision(decision.value),
                decided_by_discord_id=interaction.user.id,
                staff_notes=notes,
            )

        logger.info(
            "Application %s decided as %s by %s",
            application_id,
            decision.value,
            interaction.user,
        )
        await interaction.response.send_message(
            f"Application `{application_id}` marked as **{decision.name}** by {interaction.user.mention}."
            + (f"\nNotes: {notes}" if notes else ""),
        )

    @review.error
    async def review_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "You need `Manage Server` permission to review applications.", ephemeral=True
            )
        else:
            logger.error("Unhandled error in /recruit review: %s", error)
            await interaction.response.send_message("Something went wrong.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    cog = RecruitmentCog(bot)
    await bot.add_cog(cog)
    bot.tree.add_command(cog.recruit_group)
