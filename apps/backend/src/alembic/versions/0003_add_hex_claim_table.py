"""Add hex_claim table

Revision ID: c8447fb674f0
Revises: b2f9c61eab47
Create Date: 2026-04-29 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c8447fb674f0"
down_revision: str | Sequence[str] | None = "b2f9c61eab47"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "hex_claim",
        sa.Column("upload_uid", sa.String(length=36), nullable=False),
        sa.Column("user_uid", sa.String(length=36), nullable=False),
        sa.Column("h3_cell", sa.String(length=15), nullable=False),
        sa.Column("h3_resolution", sa.Integer(), nullable=False),
        sa.Column("polygon_index", sa.Integer(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("git_sha", sa.String(length=40), nullable=True),
        sa.Column("uid", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["upload_uid"],
            ["upload.uid"],
        ),
        sa.ForeignKeyConstraint(
            ["user_uid"],
            ["user.uid"],
        ),
        sa.PrimaryKeyConstraint("uid"),
    )
    with op.batch_alter_table("hex_claim", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_hex_claim_uid"), ["uid"], unique=False)
        batch_op.create_index(
            batch_op.f("ix_hex_claim_upload_uid"), ["upload_uid"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_hex_claim_user_uid"), ["user_uid"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_hex_claim_h3_cell"), ["h3_cell"], unique=False
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("hex_claim", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_hex_claim_h3_cell"))
        batch_op.drop_index(batch_op.f("ix_hex_claim_user_uid"))
        batch_op.drop_index(batch_op.f("ix_hex_claim_upload_uid"))
        batch_op.drop_index(batch_op.f("ix_hex_claim_uid"))

    op.drop_table("hex_claim")
