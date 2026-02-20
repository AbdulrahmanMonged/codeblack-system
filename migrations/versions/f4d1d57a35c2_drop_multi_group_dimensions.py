"""drop multi group dimensions

Revision ID: f4d1d57a35c2
Revises: 31f3f3d0a5f1
Create Date: 2026-02-20 16:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "f4d1d57a35c2"
down_revision: Union[str, None] = "31f3f3d0a5f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _drop_index_if_exists(table_name: str, index_name: str) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return
    indexes = {row["name"] for row in inspector.get_indexes(table_name)}
    if index_name in indexes:
        op.drop_index(index_name, table_name=table_name)


def _drop_unique_if_exists(table_name: str, constraint_name: str) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return
    constraints = {row["name"] for row in inspector.get_unique_constraints(table_name)}
    if constraint_name in constraints:
        op.drop_constraint(constraint_name, table_name, type_="unique")


def _drop_fk_on_column(table_name: str, column_name: str) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return
    for fk in inspector.get_foreign_keys(table_name):
        if column_name in fk.get("constrained_columns", []) and fk.get("name"):
            op.drop_constraint(fk["name"], table_name, type_="foreignkey")


def _column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return False
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    if _column_exists("group_activities", "group_id"):
        _drop_fk_on_column("group_activities", "group_id")
        _drop_index_if_exists("group_activities", "ix_group_activities_group_id")
        op.drop_column("group_activities", "group_id")

    if _table_exists("group_ranks"):
        _drop_unique_if_exists("group_ranks", "uq_group_rank_name")
        _drop_unique_if_exists("group_ranks", "uq_group_rank_level")
        if _column_exists("group_ranks", "group_id"):
            _drop_fk_on_column("group_ranks", "group_id")
            _drop_index_if_exists("group_ranks", "ix_group_ranks_group_id")
            op.drop_column("group_ranks", "group_id")
        bind = op.get_bind()
        inspector = sa.inspect(bind)
        constraints = {row["name"] for row in inspector.get_unique_constraints("group_ranks")}
        if "uq_rank_name" not in constraints:
            op.create_unique_constraint("uq_rank_name", "group_ranks", ["name"])
        if "uq_rank_level" not in constraints:
            op.create_unique_constraint("uq_rank_level", "group_ranks", ["level"])

    if _table_exists("group_memberships"):
        _drop_unique_if_exists("group_memberships", "uq_group_player_membership")
        if _column_exists("group_memberships", "group_id"):
            _drop_fk_on_column("group_memberships", "group_id")
            _drop_index_if_exists("group_memberships", "ix_group_memberships_group_id")
            op.drop_column("group_memberships", "group_id")
        bind = op.get_bind()
        inspector = sa.inspect(bind)
        constraints = {row["name"] for row in inspector.get_unique_constraints("group_memberships")}
        if "uq_group_membership_player_id" not in constraints:
            op.create_unique_constraint(
                "uq_group_membership_player_id",
                "group_memberships",
                ["player_id"],
            )

    if _table_exists("groups"):
        _drop_index_if_exists("groups", "ix_groups_code")
        op.drop_table("groups")


def downgrade() -> None:
    op.create_table(
        "groups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_groups_code", "groups", ["code"], unique=True)
    op.execute(
        sa.text(
            "INSERT INTO groups (code, name, is_active) "
            "VALUES ('REDACTED', 'CodeBlack', true)"
        )
    )

    op.drop_constraint("uq_group_membership_player_id", "group_memberships", type_="unique")
    op.add_column("group_memberships", sa.Column("group_id", sa.Integer(), nullable=True))
    op.create_index("ix_group_memberships_group_id", "group_memberships", ["group_id"], unique=False)
    op.execute(
        sa.text(
            "UPDATE group_memberships SET group_id = "
            "(SELECT id FROM groups WHERE code = 'REDACTED' LIMIT 1)"
        )
    )
    op.create_foreign_key(
        "group_memberships_group_id_fkey",
        "group_memberships",
        "groups",
        ["group_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_unique_constraint(
        "uq_group_player_membership",
        "group_memberships",
        ["group_id", "player_id"],
    )

    op.drop_constraint("uq_rank_name", "group_ranks", type_="unique")
    op.drop_constraint("uq_rank_level", "group_ranks", type_="unique")
    op.add_column("group_ranks", sa.Column("group_id", sa.Integer(), nullable=True))
    op.create_index("ix_group_ranks_group_id", "group_ranks", ["group_id"], unique=False)
    op.execute(
        sa.text(
            "UPDATE group_ranks SET group_id = "
            "(SELECT id FROM groups WHERE code = 'REDACTED' LIMIT 1)"
        )
    )
    op.create_foreign_key(
        "group_ranks_group_id_fkey",
        "group_ranks",
        "groups",
        ["group_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_unique_constraint("uq_group_rank_name", "group_ranks", ["group_id", "name"])
    op.create_unique_constraint("uq_group_rank_level", "group_ranks", ["group_id", "level"])

    op.add_column("group_activities", sa.Column("group_id", sa.Integer(), nullable=True))
    op.create_index("ix_group_activities_group_id", "group_activities", ["group_id"], unique=False)
    op.execute(
        sa.text(
            "UPDATE group_activities SET group_id = "
            "(SELECT id FROM groups WHERE code = 'REDACTED' LIMIT 1)"
        )
    )
    op.create_foreign_key(
        "group_activities_group_id_fkey",
        "group_activities",
        "groups",
        ["group_id"],
        ["id"],
        ondelete="CASCADE",
    )
