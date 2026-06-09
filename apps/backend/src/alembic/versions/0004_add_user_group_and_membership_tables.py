"""Add user_group and user_group_membership tables

Revision ID: d7e3a2b9f4c1
Revises: c8447fb674f0
Create Date: 2026-05-15 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d7e3a2b9f4c1"
down_revision: str | Sequence[str] | None = "c8447fb674f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "user_group",
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("owner_uid", sa.String(length=36), nullable=False),
        sa.Column("archived", sa.Boolean(), nullable=False),
        sa.Column("uid", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_uid"],
            ["user.uid"],
        ),
        sa.PrimaryKeyConstraint("uid"),
    )
    with op.batch_alter_table("user_group", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_user_group_uid"), ["uid"], unique=False)
        batch_op.create_index(
            batch_op.f("ix_user_group_owner_uid"),
            ["owner_uid"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_user_group_archived"), ["archived"], unique=False
        )

    op.create_table(
        "user_group_membership",
        sa.Column("user_uid", sa.String(length=36), nullable=False),
        sa.Column("user_group_uid", sa.String(length=36), nullable=False),
        sa.Column("uid", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_uid"],
            ["user.uid"],
        ),
        sa.ForeignKeyConstraint(
            ["user_group_uid"],
            ["user_group.uid"],
        ),
        sa.PrimaryKeyConstraint("uid"),
        sa.UniqueConstraint(
            "user_uid",
            "user_group_uid",
            name="uq_user_group_membership_user_group",
        ),
    )
    with op.batch_alter_table("user_group_membership", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_user_group_membership_uid"), ["uid"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_user_group_membership_user_uid"),
            ["user_uid"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_user_group_membership_user_group_uid"),
            ["user_group_uid"],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("user_group_membership", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_user_group_membership_user_group_uid"))
        batch_op.drop_index(batch_op.f("ix_user_group_membership_user_uid"))
        batch_op.drop_index(batch_op.f("ix_user_group_membership_uid"))

    op.drop_table("user_group_membership")

    with op.batch_alter_table("user_group", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_user_group_archived"))
        batch_op.drop_index(batch_op.f("ix_user_group_owner_uid"))
        batch_op.drop_index(batch_op.f("ix_user_group_uid"))

    op.drop_table("user_group")
