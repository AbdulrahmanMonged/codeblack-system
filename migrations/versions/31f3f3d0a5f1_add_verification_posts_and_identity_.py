"""add verification posts and identity extensions

Revision ID: 31f3f3d0a5f1
Revises: b6e8dcb19a40
Create Date: 2026-02-20 16:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "31f3f3d0a5f1"
down_revision: Union[str, None] = "b6e8dcb19a40"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return False
    return any(
        column["name"] == column_name
        for column in inspector.get_columns(table_name)
    )


def _index_exists(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return False
    return any(
        index["name"] == index_name
        for index in inspector.get_indexes(table_name)
    )


def _foreign_key_exists(
    table_name: str,
    *,
    constrained_columns: tuple[str, ...],
    referred_table: str,
    referred_columns: tuple[str, ...],
) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return False
    for fk in inspector.get_foreign_keys(table_name):
        if (
            tuple(fk.get("constrained_columns") or ()) == constrained_columns
            and str(fk.get("referred_table") or "") == referred_table
            and tuple(fk.get("referred_columns") or ()) == referred_columns
        ):
            return True
    return False


def upgrade() -> None:
    if not _table_exists("verification_requests"):
        op.create_table(
            "verification_requests",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("public_id", sa.String(length=64), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("discord_user_id", sa.BigInteger(), nullable=False),
            sa.Column("account_name", sa.String(length=255), nullable=False),
            sa.Column("mta_serial", sa.String(length=64), nullable=False),
            sa.Column("forum_url", sa.String(length=1024), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("review_comment", sa.Text(), nullable=True),
            sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
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
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
    if not _index_exists("verification_requests", op.f("ix_verification_requests_public_id")):
        op.create_index(
            op.f("ix_verification_requests_public_id"),
            "verification_requests",
            ["public_id"],
            unique=True,
        )
    if not _index_exists("verification_requests", op.f("ix_verification_requests_user_id")):
        op.create_index(
            op.f("ix_verification_requests_user_id"),
            "verification_requests",
            ["user_id"],
            unique=False,
        )
    if not _index_exists("verification_requests", op.f("ix_verification_requests_discord_user_id")):
        op.create_index(
            op.f("ix_verification_requests_discord_user_id"),
            "verification_requests",
            ["discord_user_id"],
            unique=False,
        )
    if not _index_exists("verification_requests", op.f("ix_verification_requests_account_name")):
        op.create_index(
            op.f("ix_verification_requests_account_name"),
            "verification_requests",
            ["account_name"],
            unique=False,
        )
    if not _index_exists("verification_requests", op.f("ix_verification_requests_status")):
        op.create_index(
            op.f("ix_verification_requests_status"),
            "verification_requests",
            ["status"],
            unique=False,
        )

    if not _table_exists("landing_posts"):
        op.create_table(
            "landing_posts",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("public_id", sa.String(length=64), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("media_url", sa.String(length=2048), nullable=True),
            sa.Column("is_published", sa.Boolean(), server_default="false", nullable=False),
            sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_by_user_id", sa.Integer(), nullable=True),
            sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
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
            sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
    if not _index_exists("landing_posts", op.f("ix_landing_posts_public_id")):
        op.create_index(op.f("ix_landing_posts_public_id"), "landing_posts", ["public_id"], unique=True)
    if not _index_exists("landing_posts", op.f("ix_landing_posts_is_published")):
        op.create_index(op.f("ix_landing_posts_is_published"), "landing_posts", ["is_published"], unique=False)
    if not _index_exists("landing_posts", op.f("ix_landing_posts_published_at")):
        op.create_index(op.f("ix_landing_posts_published_at"), "landing_posts", ["published_at"], unique=False)
    if not _index_exists("landing_posts", op.f("ix_landing_posts_created_at")):
        op.create_index(op.f("ix_landing_posts_created_at"), "landing_posts", ["created_at"], unique=False)

    if not _column_exists("discord_roles", "color_int"):
        op.add_column(
            "discord_roles",
            sa.Column("color_int", sa.Integer(), server_default="0", nullable=False),
        )
    if not _column_exists("voting_votes", "comment_text"):
        op.add_column("voting_votes", sa.Column("comment_text", sa.Text(), nullable=True))

    if not _column_exists("user_game_accounts", "mta_serial"):
        op.add_column("user_game_accounts", sa.Column("mta_serial", sa.String(length=64), nullable=True))
    if not _column_exists("user_game_accounts", "forum_url"):
        op.add_column("user_game_accounts", sa.Column("forum_url", sa.String(length=1024), nullable=True))
    if not _column_exists("user_game_accounts", "verified_at"):
        op.add_column("user_game_accounts", sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True))
    if not _column_exists("user_game_accounts", "verified_by_user_id"):
        op.add_column("user_game_accounts", sa.Column("verified_by_user_id", sa.Integer(), nullable=True))
    if not _index_exists("user_game_accounts", op.f("ix_user_game_accounts_mta_serial")):
        op.create_index(
            op.f("ix_user_game_accounts_mta_serial"),
            "user_game_accounts",
            ["mta_serial"],
            unique=False,
        )
    if _column_exists("user_game_accounts", "verified_by_user_id") and not _foreign_key_exists(
        "user_game_accounts",
        constrained_columns=("verified_by_user_id",),
        referred_table="users",
        referred_columns=("id",),
    ):
        op.create_foreign_key(
            "fk_user_game_accounts_verified_by_user_id",
            "user_game_accounts",
            "users",
            ["verified_by_user_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    op.drop_constraint(
        "fk_user_game_accounts_verified_by_user_id",
        "user_game_accounts",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_user_game_accounts_mta_serial"), table_name="user_game_accounts")
    op.drop_column("user_game_accounts", "verified_by_user_id")
    op.drop_column("user_game_accounts", "verified_at")
    op.drop_column("user_game_accounts", "forum_url")
    op.drop_column("user_game_accounts", "mta_serial")

    op.drop_column("voting_votes", "comment_text")
    op.drop_column("discord_roles", "color_int")

    op.drop_index(op.f("ix_landing_posts_created_at"), table_name="landing_posts")
    op.drop_index(op.f("ix_landing_posts_published_at"), table_name="landing_posts")
    op.drop_index(op.f("ix_landing_posts_is_published"), table_name="landing_posts")
    op.drop_index(op.f("ix_landing_posts_public_id"), table_name="landing_posts")
    op.drop_table("landing_posts")

    op.drop_index(op.f("ix_verification_requests_status"), table_name="verification_requests")
    op.drop_index(op.f("ix_verification_requests_account_name"), table_name="verification_requests")
    op.drop_index(op.f("ix_verification_requests_discord_user_id"), table_name="verification_requests")
    op.drop_index(op.f("ix_verification_requests_user_id"), table_name="verification_requests")
    op.drop_index(op.f("ix_verification_requests_public_id"), table_name="verification_requests")
    op.drop_table("verification_requests")
