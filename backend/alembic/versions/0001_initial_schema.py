"""Initial schema: members and applications

Revision ID: 0001
Revises:
Create Date: 2026-07-07

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

member_status_enum = sa.Enum(
    "applicant", "active", "inactive", "staff", "left", "banned", name="memberstatus"
)
application_decision_enum = sa.Enum(
    "pending", "accepted", "interview", "declined", name="applicationdecision"
)
ai_recommendation_enum = sa.Enum(
    "accept", "interview", "decline", name="airecommendation"
)


def upgrade() -> None:
    op.create_table(
        "members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("discord_id", sa.BigInteger(), nullable=False),
        sa.Column("discord_username", sa.String(length=128), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=True),
        sa.Column("status", member_status_enum, nullable=False, server_default="applicant"),
        sa.Column("rank", sa.String(length=64), nullable=True),
        sa.Column("join_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("left_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("message_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("voice_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("events_attended", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("warnings", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("recruitments_made", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_members_discord_id", "members", ["discord_id"], unique=True)

    op.create_table(
        "applications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("member_id", sa.Integer(), sa.ForeignKey("members.id"), nullable=False),
        sa.Column("answers", sa.JSON(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("ai_score", sa.Float(), nullable=True),
        sa.Column("ai_activity_score", sa.Float(), nullable=True),
        sa.Column("ai_maturity_score", sa.Float(), nullable=True),
        sa.Column("ai_communication_score", sa.Float(), nullable=True),
        sa.Column("ai_teamwork_score", sa.Float(), nullable=True),
        sa.Column("ai_honesty_score", sa.Float(), nullable=True),
        sa.Column("ai_toxicity_risk_score", sa.Float(), nullable=True),
        sa.Column("ai_long_term_potential_score", sa.Float(), nullable=True),
        sa.Column("ai_explanation", sa.Text(), nullable=True),
        sa.Column("ai_positives", sa.JSON(), nullable=True),
        sa.Column("ai_concerns", sa.JSON(), nullable=True),
        sa.Column("ai_recommendation", ai_recommendation_enum, nullable=True),
        sa.Column("ai_evaluated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ai_model_used", sa.String(length=64), nullable=True),
        sa.Column("ai_raw_response", sa.JSON(), nullable=True),
        sa.Column(
            "decision",
            application_decision_enum,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("decided_by_discord_id", sa.BigInteger(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("staff_notes", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("applications")
    op.drop_index("ix_members_discord_id", table_name="members")
    op.drop_table("members")
    ai_recommendation_enum.drop(op.get_bind(), checkfirst=True)
    application_decision_enum.drop(op.get_bind(), checkfirst=True)
    member_status_enum.drop(op.get_bind(), checkfirst=True)
