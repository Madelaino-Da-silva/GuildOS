"""
ORM model registry.

Import every model module here so that:
  1. `Base.metadata` is fully populated when Alembic autogenerates migrations.
  2. Other modules can do `from app.models import Member, Application`.

Future features (events, reports, promotions, moderation flags) will add
their model modules here as they're built.
"""
from app.models.application import AIRecommendation, Application, ApplicationDecision
from app.models.member import Member, MemberStatus

__all__ = [
    "Member",
    "MemberStatus",
    "Application",
    "ApplicationDecision",
    "AIRecommendation",
]
