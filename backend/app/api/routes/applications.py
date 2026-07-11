"""
Application API routes.

Used by:
  - The Discord bot (submitting new applications via /apply)
  - The dashboard (listing applications, viewing AI evaluations, recording
    staff decisions)

Authentication: submission is called by the bot with an internal service
token (see app.core.security); dashboard-facing read/decision routes
require a logged-in staff JWT (wired up when the Dashboard/Auth feature
is built — see TODO markers below).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.logging import get_logger
from app.models.application import Application, ApplicationDecision
from app.schemas.application import (
    ApplicationDecisionUpdate,
    ApplicationOut,
    ApplicationSubmit,
)
from app.services.recruitment_service import record_staff_decision, submit_application

router = APIRouter(prefix="/applications", tags=["applications"])
logger = get_logger("guildos.api.applications")


@router.post("", response_model=ApplicationOut, status_code=status.HTTP_201_CREATED)
async def create_application(
    payload: ApplicationSubmit, db: AsyncSession = Depends(get_db)
) -> Application:
    """Submit a new application (called by the Discord bot's /apply flow)."""
    application = await submit_application(
        db,
        discord_id=payload.discord_id,
        discord_username=payload.discord_username,
        answers=payload.answers,
    )
    logger.info(
        "Application %s submitted for discord_id=%s", application.id, payload.discord_id
    )
    return application


@router.get("", response_model=list[ApplicationOut])
async def list_applications(
    decision: ApplicationDecision | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> list[Application]:
    """List applications, optionally filtered by decision status. Used by
    the dashboard's Applications page.
    """
    # TODO(dashboard-auth): require staff JWT once the auth route is built.
    query = select(Application).order_by(Application.submitted_at.desc()).limit(limit).offset(offset)
    if decision is not None:
        query = query.where(Application.decision == decision)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/{application_id}", response_model=ApplicationOut)
async def get_application(application_id: int, db: AsyncSession = Depends(get_db)) -> Application:
    application = await db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


@router.post("/{application_id}/decision", response_model=ApplicationOut)
async def decide_application(
    application_id: int,
    payload: ApplicationDecisionUpdate,
    db: AsyncSession = Depends(get_db),
) -> Application:
    """Record a human staff decision on an application. This is the ONLY
    endpoint that changes an application's decision — never done by the AI.
    """
    # TODO(dashboard-auth): require staff JWT and verify staff role once
    # the auth system is built; for now decided_by_discord_id is
    # supplied directly by the caller (bot command or dashboard action).
    result = await db.execute(
        select(Application)
        .options(selectinload(Application.member))
        .where(Application.id == application_id)
    )
    application = result.scalar_one_or_none()
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")

    updated = await record_staff_decision(
        db,
        application,
        decision=payload.decision,
        decided_by_discord_id=payload.decided_by_discord_id,
        staff_notes=payload.staff_notes,
    )
    logger.info(
        "Application %s decided as %s by discord_id=%s",
        application_id,
        payload.decision,
        payload.decided_by_discord_id,
    )
    return updated
