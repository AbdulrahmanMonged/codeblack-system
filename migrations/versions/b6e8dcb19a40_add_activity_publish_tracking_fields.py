"""add activity publish tracking fields

Revision ID: b6e8dcb19a40
Revises: 4d2b1f9ce777
Create Date: 2026-02-19 17:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b6e8dcb19a40"
down_revision: Union[str, None] = "4d2b1f9ce777"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "group_activities",
        sa.Column("publish_attempts", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "group_activities",
        sa.Column("last_publish_error", sa.Text(), nullable=True),
    )
    op.add_column(
        "group_activities",
        sa.Column("last_publish_attempt_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("group_activities", "last_publish_attempt_at")
    op.drop_column("group_activities", "last_publish_error")
    op.drop_column("group_activities", "publish_attempts")
