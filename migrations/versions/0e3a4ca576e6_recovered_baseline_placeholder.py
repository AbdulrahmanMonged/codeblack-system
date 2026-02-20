"""recovered baseline placeholder

Revision ID: 0e3a4ca576e6
Revises: 
Create Date: 2026-02-19 14:30:00.000000

This revision was missing after workspace recovery. It is intentionally
non-destructive and acts as a graph placeholder so later revisions
(`8f5f18d3c7a1` and above) can be resolved.
"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "0e3a4ca576e6"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Placeholder only: no schema operations.
    pass


def downgrade() -> None:
    # Placeholder only: no schema operations.
    pass
