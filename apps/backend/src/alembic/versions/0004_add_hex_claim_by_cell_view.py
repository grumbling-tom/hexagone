"""Add hex_claim_by_cell view

Revision ID: 1744868a3b50
Revises: c8447fb674f0
Create Date: 2026-05-05 16:30:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1744868a3b50"
down_revision: str | Sequence[str] | None = "c8447fb674f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Imported lazily so that loading this module (e.g. in the
    # validate-migrations pre-commit hook, which only walks revisions
    # via ``ScriptDirectory.walk_revisions``) doesn't drag in
    # ``src.app.settings`` and demand DEV runtime credentials.
    from src.app.repository.views import HexClaimByCell  # noqa: PLC0415

    # Compile the SELECT to a literal string against the bind's actual
    # dialect, then ``op.execute`` the resulting plain string. We
    # deliberately avoid ``op.execute(<DDLElement>)`` here — the
    # ``@compiler.compiles(CreateView)`` dispatch doesn't always fire
    # in the migration context, and the silent fallback compiles only
    # the inner ``SELECT`` (Postgres runs it as a query, no view is
    # created, no error). A literal CREATE VIEW string is bullet-proof.
    selectable_sql = HexClaimByCell.__view_selectable__.compile(
        dialect=op.get_bind().dialect,
        compile_kwargs={"literal_binds": True},
    )
    view_name = HexClaimByCell.__table__.name
    op.execute(f"CREATE VIEW {view_name} AS {selectable_sql}")


def downgrade() -> None:
    """Downgrade schema."""
    from src.app.repository.views import HexClaimByCell  # noqa: PLC0415

    op.execute(f"DROP VIEW IF EXISTS {HexClaimByCell.__table__.name}")
