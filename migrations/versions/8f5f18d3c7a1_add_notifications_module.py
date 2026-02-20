"""add notifications module

Revision ID: 8f5f18d3c7a1
Revises: 0e3a4ca576e6
Create Date: 2026-02-19 15:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "8f5f18d3c7a1"
down_revision: Union[str, None] = "0e3a4ca576e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("public_id", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=True),
        sa.Column("entity_public_id", sa.String(length=128), nullable=True),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notifications_actor_user_id"), "notifications", ["actor_user_id"], unique=False)
    op.create_index(op.f("ix_notifications_category"), "notifications", ["category"], unique=False)
    op.create_index(op.f("ix_notifications_created_at"), "notifications", ["created_at"], unique=False)
    op.create_index(op.f("ix_notifications_entity_public_id"), "notifications", ["entity_public_id"], unique=False)
    op.create_index(op.f("ix_notifications_entity_type"), "notifications", ["entity_type"], unique=False)
    op.create_index(op.f("ix_notifications_event_type"), "notifications", ["event_type"], unique=False)
    op.create_index(op.f("ix_notifications_public_id"), "notifications", ["public_id"], unique=True)

    op.create_table(
        "notification_deliveries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("notification_id", sa.Integer(), nullable=False),
        sa.Column("recipient_user_id", sa.Integer(), nullable=False),
        sa.Column("is_read", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["notification_id"], ["notifications.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recipient_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "notification_id",
            "recipient_user_id",
            name="uq_notification_delivery_notification_recipient",
        ),
    )
    op.create_index(
        op.f("ix_notification_deliveries_notification_id"),
        "notification_deliveries",
        ["notification_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_notification_deliveries_recipient_user_id"),
        "notification_deliveries",
        ["recipient_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_notification_deliveries_recipient_user_id"),
        table_name="notification_deliveries",
    )
    op.drop_index(
        op.f("ix_notification_deliveries_notification_id"),
        table_name="notification_deliveries",
    )
    op.drop_table("notification_deliveries")

    op.drop_index(op.f("ix_notifications_public_id"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_event_type"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_entity_type"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_entity_public_id"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_created_at"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_category"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_actor_user_id"), table_name="notifications")
    op.drop_table("notifications")
