"""Add procrastinate schema

Revision ID: b1c2d3e4f5a6
Revises: ac5e9a75bedf
Create Date: 2026-06-12 00:00:00.000000

Procrastinate (the Postgres-backed task queue powering the upload worker) owns
its own ``procrastinate_*`` tables, types, functions and triggers. Rather than
applying them out of band (``procrastinate schema --apply`` via a separate Job),
we let Alembic own them so a single ``alembic upgrade head`` provisions the whole
database — the migrate initContainer and the docker-compose migrate service need
no extra step.

This applies Procrastinate's packaged baseline schema verbatim:
``procrastinate/sql/schema.sql`` (read via importlib.resources). Autogenerate is
told to leave these objects alone by the ``procrastinate_*`` guard in
``src/alembic/env.py`` — they aren't in ``BaseModel.metadata``.

Upgrading Procrastinate: a version bump that ships schema changes ships delta
SQL under ``procrastinate/sql/migrations/`` (see ``procrastinate schema
--migrations-path``). Apply each delta as its own follow-up Alembic migration
(``op.get_bind().exec_driver_sql(...)``); do not re-run this baseline.
"""

from importlib.resources import files

from alembic import op

# revision identifiers, used by Alembic.
revision = "b1c2d3e4f5a6"
down_revision = "ac5e9a75bedf"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade schema."""
    schema_sql = files("procrastinate.sql").joinpath("schema.sql").read_text()
    # op.execute runs the whole multi-statement script verbatim. SQLAlchemy's
    # text() leaves the ``::`` casts alone (they aren't parsed as bind params),
    # so no escaping is needed.
    op.execute(schema_sql)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop everything Procrastinate owns by name prefix (resilient to which exact
    # objects the installed version created). Tables first with CASCADE to take
    # their triggers/indexes/FKs, then routines, then types.
    op.execute(
        """
        DO $$
        DECLARE
            obj record;
        BEGIN
            FOR obj IN
                SELECT tablename FROM pg_tables
                WHERE schemaname = current_schema()
                  AND tablename LIKE 'procrastinate_%'
            LOOP
                EXECUTE 'DROP TABLE IF EXISTS '
                    || quote_ident(obj.tablename) || ' CASCADE';
            END LOOP;

            FOR obj IN
                SELECT p.oid::regprocedure AS sig FROM pg_proc p
                JOIN pg_namespace n ON n.oid = p.pronamespace
                WHERE n.nspname = current_schema()
                  AND p.proname LIKE 'procrastinate_%'
            LOOP
                EXECUTE 'DROP FUNCTION IF EXISTS ' || obj.sig || ' CASCADE';
            END LOOP;

            FOR obj IN
                SELECT t.typname FROM pg_type t
                JOIN pg_namespace n ON n.oid = t.typnamespace
                WHERE n.nspname = current_schema()
                  AND t.typname LIKE 'procrastinate_%'
            LOOP
                EXECUTE 'DROP TYPE IF EXISTS '
                    || quote_ident(obj.typname) || ' CASCADE';
            END LOOP;
        END $$;
        """
    )
