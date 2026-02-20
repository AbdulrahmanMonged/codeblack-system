"""drop application raw_text column

Revision ID: 9c1a2e74e6b3
Revises: f4d1d57a35c2
Create Date: 2026-02-20 18:20:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "9c1a2e74e6b3"
down_revision: Union[str, None] = "f4d1d57a35c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("applications")}
    if "raw_text" in columns:
        op.drop_column("applications", "raw_text")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("applications")}
    if "raw_text" not in columns:
        op.add_column("applications", sa.Column("raw_text", sa.Text(), nullable=True))
