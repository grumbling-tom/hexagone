"""Add upload and upload_status tables

Revision ID: b2f9c61eab47
Revises: a1e8f50dfa36
Create Date: 2026-03-06 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2f9c61eab47"
down_revision: str | Sequence[str] | None = "a1e8f50dfa36"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "upload",
        sa.Column("user_uid", sa.String(length=36), nullable=False),
        sa.Column("original_filename", sa.String(), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("s3_key", sa.String(), nullable=False),
        sa.Column("uid", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_uid"],
            ["user.uid"],
        ),
        sa.PrimaryKeyConstraint("uid"),
        sa.UniqueConstraint("s3_key"),
    )
    with op.batch_alter_table("upload", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_upload_uid"), ["uid"], unique=False)
        batch_op.create_index(
            batch_op.f("ix_upload_user_uid"), ["user_uid"], unique=False
        )

    op.create_table(
        "upload_status",
        sa.Column("upload_uid", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("git_sha", sa.String(length=40), nullable=True),
        sa.Column("detail", sa.String(), nullable=True),
        sa.Column("uid", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('UPLOAD_PENDING', 'UPLOAD_RECEIVED',"
            " 'UPLOAD_SUCCESS', 'UPLOAD_INVALID')",
            name="ck_upload_status_value",
        ),
        sa.ForeignKeyConstraint(
            ["upload_uid"],
            ["upload.uid"],
        ),
        sa.PrimaryKeyConstraint("uid"),
    )
    with op.batch_alter_table("upload_status", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_upload_status_uid"), ["uid"], unique=False)
        batch_op.create_index(
            batch_op.f("ix_upload_status_upload_uid"), ["upload_uid"], unique=False
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("upload_status", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_upload_status_upload_uid"))
        batch_op.drop_index(batch_op.f("ix_upload_status_uid"))

    op.drop_table("upload_status")

    with op.batch_alter_table("upload", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_upload_user_uid"))
        batch_op.drop_index(batch_op.f("ix_upload_uid"))

    op.drop_table("upload")
