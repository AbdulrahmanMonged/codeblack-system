"""add backend voting module

Revision ID: 4d2b1f9ce777
Revises: 8f5f18d3c7a1
Create Date: 2026-02-19 17:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "4d2b1f9ce777"
down_revision: Union[str, None] = "8f5f18d3c7a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "voting_contexts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("context_type", sa.String(length=64), nullable=False),
        sa.Column("context_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("opened_by_user_id", sa.Integer(), nullable=True),
        sa.Column(
            "opened_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("closed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("close_reason", sa.Text(), nullable=True),
        sa.Column("auto_close_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["closed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["opened_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("context_type", "context_id", name="uq_voting_context_type_id"),
    )
    op.create_index(op.f("ix_voting_contexts_auto_close_at"), "voting_contexts", ["auto_close_at"], unique=False)
    op.create_index(op.f("ix_voting_contexts_closed_by_user_id"), "voting_contexts", ["closed_by_user_id"], unique=False)
    op.create_index(op.f("ix_voting_contexts_context_id"), "voting_contexts", ["context_id"], unique=False)
    op.create_index(op.f("ix_voting_contexts_context_type"), "voting_contexts", ["context_type"], unique=False)
    op.create_index(op.f("ix_voting_contexts_opened_by_user_id"), "voting_contexts", ["opened_by_user_id"], unique=False)

    op.create_table(
        "voting_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("voting_context_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("target_user_id", sa.Integer(), nullable=True),
        sa.Column("vote_choice", sa.String(length=16), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["voting_context_id"], ["voting_contexts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_voting_events_actor_user_id"), "voting_events", ["actor_user_id"], unique=False)
    op.create_index(op.f("ix_voting_events_created_at"), "voting_events", ["created_at"], unique=False)
    op.create_index(op.f("ix_voting_events_event_type"), "voting_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_voting_events_target_user_id"), "voting_events", ["target_user_id"], unique=False)
    op.create_index(op.f("ix_voting_events_voting_context_id"), "voting_events", ["voting_context_id"], unique=False)

    op.create_table(
        "voting_votes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("voting_context_id", sa.Integer(), nullable=False),
        sa.Column("voter_user_id", sa.Integer(), nullable=False),
        sa.Column("choice", sa.String(length=16), nullable=False),
        sa.Column(
            "cast_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["voter_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["voting_context_id"], ["voting_contexts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "voting_context_id",
            "voter_user_id",
            name="uq_voting_vote_context_voter",
        ),
    )
    op.create_index(op.f("ix_voting_votes_voter_user_id"), "voting_votes", ["voter_user_id"], unique=False)
    op.create_index(op.f("ix_voting_votes_voting_context_id"), "voting_votes", ["voting_context_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_voting_votes_voting_context_id"), table_name="voting_votes")
    op.drop_index(op.f("ix_voting_votes_voter_user_id"), table_name="voting_votes")
    op.drop_table("voting_votes")

    op.drop_index(op.f("ix_voting_events_voting_context_id"), table_name="voting_events")
    op.drop_index(op.f("ix_voting_events_target_user_id"), table_name="voting_events")
    op.drop_index(op.f("ix_voting_events_event_type"), table_name="voting_events")
    op.drop_index(op.f("ix_voting_events_created_at"), table_name="voting_events")
    op.drop_index(op.f("ix_voting_events_actor_user_id"), table_name="voting_events")
    op.drop_table("voting_events")

    op.drop_index(op.f("ix_voting_contexts_opened_by_user_id"), table_name="voting_contexts")
    op.drop_index(op.f("ix_voting_contexts_context_type"), table_name="voting_contexts")
    op.drop_index(op.f("ix_voting_contexts_context_id"), table_name="voting_contexts")
    op.drop_index(op.f("ix_voting_contexts_closed_by_user_id"), table_name="voting_contexts")
    op.drop_index(op.f("ix_voting_contexts_auto_close_at"), table_name="voting_contexts")
    op.drop_table("voting_contexts")
