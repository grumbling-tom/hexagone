"""ORM models backed by database VIEWs.

Pattern adapted from the SQLAlchemy wiki Views recipe:
    https://github.com/sqlalchemy/sqlalchemy/wiki/Views

Each ``View`` subclass is mapped to a database VIEW (rather than a TABLE).
The ``view()`` helper returns a lightweight ``TableClause`` (NOT a ``Table``)
— it is NOT registered in ``metadata.tables``, so ``metadata.create_all``
does not try to issue a ``CREATE TABLE`` for it. Instead the helper
attaches CREATE/DROP VIEW DDL as ``after_create`` / ``before_drop`` event
listeners on the metadata.

Those listeners are guarded by ``_view_exists`` / ``_view_doesnt_exist``
so a re-import (e.g. ``importlib.reload`` or hot-reload server) cannot
cause duplicate-create failures.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any, ClassVar, cast

import sqlalchemy as sa
from sqlalchemy import event, inspect
from sqlalchemy.ext import compiler
from sqlalchemy.orm import Mapped
from sqlalchemy.schema import DDLElement
from sqlalchemy.sql.compiler import DDLCompiler
from sqlalchemy.sql.expression import TableClause

from .database import BaseModel
from .models import HexClaim


class CreateView(DDLElement):
    inherit_cache = True

    def __init__(self, name: str, selectable: sa.Select[Any]) -> None:
        self.name = name
        self.selectable = selectable


class DropView(DDLElement):
    inherit_cache = True

    def __init__(self, name: str) -> None:
        self.name = name


@compiler.compiles(CreateView)  # pyright: ignore[reportUntypedFunctionDecorator]
def _compile_create_view(  # pyright: ignore[reportUnusedFunction]
    element: CreateView,
    compiler_: DDLCompiler,
    **_kw: object,
) -> str:
    selectable_sql = compiler_.sql_compiler.process(
        element.selectable, literal_binds=True
    )
    return f"CREATE VIEW {element.name} AS {selectable_sql}"


@compiler.compiles(DropView)  # pyright: ignore[reportUntypedFunctionDecorator]
def _compile_drop_view(  # pyright: ignore[reportUnusedFunction]
    element: DropView,
    _compiler: DDLCompiler,
    **_kw: object,
) -> str:
    return f"DROP VIEW {element.name}"


# The DDL ``execute_if`` predicate signature matches ``DDLIfCallable`` but
# SQLAlchemy invokes us with the connection under the keyword ``bind``.
# We accept ``*args, **kw`` so pyright admits the predicate against the
# stricter declared signature.
def _view_exists(
    ddl: Any,  # noqa: ANN401
    *_args: Any,  # noqa: ANN401
    **_kw: Any,  # noqa: ANN401
) -> bool:
    bind = _kw.get("bind") or (_args[1] if len(_args) > 1 else None)
    return ddl.name in inspect(bind).get_view_names()  # pyright: ignore[reportOptionalMemberAccess]


def _view_doesnt_exist(
    ddl: Any,  # noqa: ANN401
    *args: Any,  # noqa: ANN401
    **kw: Any,  # noqa: ANN401
) -> bool:
    return not _view_exists(ddl, *args, **kw)


def view(
    name: str,
    metadata: sa.MetaData,
    selectable: sa.Select[Any],
    *,
    primary_key: str = "uid",
) -> TableClause:
    """Build a TableClause backed by a database VIEW.

    Returns an unregistered ``TableClause`` (lives outside
    ``metadata.tables``) and registers idempotent CREATE/DROP VIEW
    listeners on ``metadata``. The listeners fire on
    ``metadata.create_all`` / ``metadata.drop_all`` — which is what
    makes the view materialize in the in-memory SQLite test DB.

    Production migrations issue the same ``CreateView`` DDL via
    ``op.execute(create_view_ddl(<view_class>))``.

    Recipe: https://github.com/sqlalchemy/sqlalchemy/wiki/Views
    """
    columns = [
        sa.Column(
            c.name,
            c.type,
            primary_key=(c.primary_key or c.name == primary_key),
        )
        for c in selectable.selected_columns
    ]
    t = sa.table(name, *columns)
    t.primary_key.update(c for c in t.c if c.primary_key)  # pyright: ignore[reportAttributeAccessIssue,reportUnknownMemberType]

    event.listen(
        metadata,
        "after_create",
        CreateView(name, selectable).execute_if(callable_=_view_doesnt_exist),
    )
    event.listen(
        metadata,
        "before_drop",
        DropView(name).execute_if(callable_=_view_exists),
    )
    return t


class View(BaseModel):
    """Abstract base for ORM models backed by database VIEWs.

    Subclasses must:
      * Set ``__view_selectable__`` to a SQLAlchemy ``select(...)``
        whose columns include synthetic ``uid`` and ``created_at`` to
        satisfy ``BaseModel``'s requirements.
      * Set ``__table__ = view(<name>, BaseModel.metadata,
        cls.__view_selectable__)``.

    See ``HexClaimByCell`` for the canonical example.
    """

    __abstract__ = True

    if TYPE_CHECKING:
        __view_selectable__: sa.Select[Any]
        __view_name__: ClassVar[str]

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        if cls.__dict__.get("__abstract__", False):
            return
        if getattr(cls, "__table__", None) is None:
            msg = f"{cls.__name__} must set __table__ = view(...)"
            raise TypeError(msg)
        # Cache the view name as a plain ``str`` class attribute so
        # ``view_class.__view_name__`` resolves without descriptor magic
        # for type checkers and IDE tooling.
        cls.__view_name__ = cast(TableClause, cls.__table__).name


def create_view_ddl(view_class: type[View]) -> CreateView:
    """Return the CreateView DDL for use in an Alembic migration.

    The migration calls ``op.execute(create_view_ddl(MyView))`` so the
    view's name AND selectable are read from the same source as the
    runtime registration — they cannot drift.
    """
    return CreateView(view_class.__view_name__, view_class.__view_selectable__)


def drop_view_ddl(view_class: type[View]) -> DropView:
    """Return the DropView DDL for use in an Alembic migration."""
    return DropView(view_class.__view_name__)


# ---------------------------------------------------------------------------
# Concrete views
# ---------------------------------------------------------------------------


class HexClaimByCell(View):
    """One row per (user, H3 cell): rolled-up claim metadata.

    Backed by the ``hex_claim_by_cell`` view. Read-only — never
    insert/update/delete.

    The synthetic ``uid`` (``user_uid || ':' || h3_cell``) satisfies
    ``Repository``'s tie-breaker requirement; ``(user_uid, h3_cell)`` is
    unique by construction so the concatenation is collision-free. The
    synthetic ``created_at`` (``MIN(created_at)``) satisfies
    ``BaseModel`` and equals ``first_claimed_at`` semantically.
    """

    __view_selectable__ = sa.select(
        (HexClaim.user_uid + sa.literal(":") + HexClaim.h3_cell).label("uid"),
        sa.func.min(HexClaim.created_at).label("created_at"),
        HexClaim.user_uid.label("user_uid"),
        HexClaim.h3_cell.label("h3_cell"),
        sa.func.count().label("claim_count"),
        sa.func.count(sa.func.distinct(HexClaim.upload_uid)).label("upload_count"),
        sa.func.min(HexClaim.created_at).label("first_claimed_at"),
        sa.func.max(HexClaim.created_at).label("last_claimed_at"),
    ).group_by(HexClaim.user_uid, HexClaim.h3_cell)

    __table__ = view(
        "hex_claim_by_cell",
        BaseModel.metadata,
        __view_selectable__,
    )

    # ``Mapped[...]`` annotations are reconciled by name against the columns
    # on ``__table__`` — they give static type checkers ``InstrumentedAttribute[T]``
    # at the class level (so ``HexClaimByCell.h3_cell`` typechecks against
    # ``Repository.get_filtered``'s ``sort_field`` parameter without a cast).
    user_uid: Mapped[str]
    h3_cell: Mapped[str]
    claim_count: Mapped[int]
    upload_count: Mapped[int]
    first_claimed_at: Mapped[datetime]
    last_claimed_at: Mapped[datetime]
