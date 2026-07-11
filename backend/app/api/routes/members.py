"""Member API routes — read access used by the dashboard's Members page."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.member import Member, MemberStatus
from app.schemas.member import MemberOut

router = APIRouter(prefix="/members", tags=["members"])


@router.get("", response_model=list[MemberOut])
async def list_members(
    status: MemberStatus | None = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> list[Member]:
    query = select(Member).order_by(Member.discord_username).limit(limit).offset(offset)
    if status is not None:
        query = query.where(Member.status == status)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/{member_id}", response_model=MemberOut)
async def get_member(member_id: int, db: AsyncSession = Depends(get_db)) -> Member:
    member = await db.get(Member, member_id)
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    return member
