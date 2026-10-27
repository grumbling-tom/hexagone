from typing import TYPE_CHECKING, Any

from sqlalchemy import asc, desc, event, inspect, select
from sqlalchemy import delete as sa_delete
from sqlalchemy import update as sa_update

from ..settings import settings
from ..utils import HIDDEN_FIELDS_KEY, Cursor, PaginatedResult, SortOrder
from .database import BaseModel
from .gating import gate
from .policy import Operation, Policy
from .predicates import Anyone, Equals, Nobody

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

    from sqlalchemy.orm import InstrumentedAttribute, Session

    from .predicates import Predicate


class NotAuthorisedError(Exception):
    """A write guard rejected the write (in memory for CREATE, in SQL otherwise)."""


class UnsortableFieldError(ValueError):
    """The requested sort field isn't visible to every viewer on every row.

    ``ORDER BY email`` would reveal the ordering of hidden emails, and the
    pagination cursor would have to encode a value the viewer may not see.
    """


class PolicyConflictError(RuntimeError):
    """One ORM instance was asked to carry two different views of a row.

    The session's identity map holds ONE instance per row, and masks live on
    that instance. If a read under one policy hid a field and a later read in
    the same session would show it (typically ``SystemPolicy`` after a
    viewer read), there is no correct value to return: un-hiding leaks to the
    earlier holder, keeping it hidden hands the system code ``REDACTED``.
    Use a separate session for the second read.
    """


def hide(entity: BaseModel, names: Iterable[str]) -> None:
    """Mask ``names`` on ``entity`` for the rest of its session.

    Unions, never replaces: a mask is only ever added.
    """
    inspect(entity).info.setdefault(HIDDEN_FIELDS_KEY, set()).update(names)


def hidden_fields(entity: BaseModel) -> frozenset[str]:
    """Return the names currently masked on ``entity``."""
    return frozenset(inspect(entity).info.get(HIDDEN_FIELDS_KEY, ()))


class UnscopedWriteError(RuntimeError):
    """A loaded instance was modified or deleted outside ``ScopedRepository``.

    ``user.email = "x"; uow.commit()`` would be flushed by the ORM's unit of
    work without consulting any policy. All writes go through
    ``ScopedRepository.update``/``delete`` (Core statements that never dirty an
    instance) or ``create`` (new instances only).
    """


def _reject_unscoped_writes(session: Session, *_: object) -> None:
    changed = [o for o in session.dirty if session.is_modified(o)]
    if changed or session.deleted:
        names = sorted({type(o).__name__ for o in [*changed, *session.deleted]})
        msg = f"Unscoped write to {names}; use ScopedRepository.update/delete"
        raise UnscopedWriteError(msg)


def forbid_unscoped_writes(db: Session) -> None:
    """Make ``db`` refuse to flush instance-level edits (idempotent)."""
    if not event.contains(db, "before_flush", _reject_unscoped_writes):
        event.listen(db, "before_flush", _reject_unscoped_writes)


class UnitOfWork:
    """The transaction boundary, and nothing else.

    Services commit through this rather than holding a ``Session``: a service
    with a ``Session`` can run any query SQLAlchemy permits, which is exactly
    what ``ScopedRepository`` exists to prevent.
    """

    def __init__(self, db: Session) -> None:
        """Wrap ``db``; only commit/rollback are exposed."""
        forbid_unscoped_writes(db)
        self._db = db

    def commit(self) -> None:
        """Commit the request's transaction."""
        self._db.commit()

    def rollback(self) -> None:
        """Roll back the request's transaction (e.g. after an IntegrityError)."""
        self._db.rollback()


class ScopedRepository[T: BaseModel]:
    """Database access for one entity, as seen by one ``Policy``.

    There is no unscoped constructor: every read is narrowed by the policy's
    row rules, every caller filter is gated by its field rules, every field
    the viewer can't see comes back as ``REDACTED``, and every write is
    guarded. Code with no viewer passes ``SystemPolicy()`` — explicitly.

    The session is private (``_db``). Nothing outside this module should touch
    it; commits go through ``UnitOfWork``.

    Type parameter:
        T: The SQLAlchemy model class type
    """

    def __init__(self, db: Session, entity: type[T], policy: Policy) -> None:
        """Bind a session, an entity and the policy every query goes through."""
        forbid_unscoped_writes(db)
        self._db = db
        self.entity = entity
        self.policy = policy

    def _masking_rules(self) -> dict[str, Predicate]:
        """READ field rules that can hide something (``Anyone`` never does)."""
        return {
            name: rule
            for name, rule in self.policy.fields(self.entity, Operation.READ).items()
            if not isinstance(rule, Anyone)
        }

    def _stamp(self, obj: T, visible: Mapping[str, Any]) -> T:
        """Mask the fields whose visibility flag came back false (or NULL)."""
        hidden = {name for name, ok in visible.items() if not ok}
        if already := hidden_fields(obj) - hidden:
            msg = (
                f"{self.entity.__name__} {obj.uid} is masked ({sorted(already)}) "
                "by an earlier read in this session; this read would show it"
            )
            raise PolicyConflictError(msg)
        if hidden:
            hide(obj, hidden)
        return obj

    def get_filtered(
        self,
        filters: Sequence[Predicate] | None = None,
        page_size: int = settings.DEFAULT_PAGE_SIZE,
        cursor: str | None = None,
        sort_field: InstrumentedAttribute[Any] | None = None,
        sort_order: SortOrder = SortOrder.ASC,
    ) -> PaginatedResult[T]:
        """Get the rows the policy lets the viewer see, filtered and paginated.

        The policy's READ row rules are ANDed in as-is (trusted); the caller's
        ``filters`` are gated first (see ``gating.gate``). Each field rule that
        can hide something is selected alongside the row as a boolean column,
        and the fields that come back false are masked on the instance.

        Args:
            filters: Caller predicates; gated against the policy's field rules.
            page_size: Number of items per page.
            cursor: Opaque cursor for the next page, None for the first page.
            sort_field: Column to sort by; must be visible to everyone.
                Defaults to the entity's uid column.
            sort_order: Sort order (default: SortOrder.ASC).

        Returns:
            Paginated result containing items and pagination metadata.

        Raises:
            ValueError: If the cursor is malformed or doesn't match the sort.
            UnsortableFieldError: If ``sort_field`` can be hidden.
        """
        if sort_field is None:
            sort_field = self.entity.uid

        sort_field_name = sort_field.name
        sort_rule = self.policy.fields(self.entity, Operation.READ).get(
            sort_field_name, Nobody()
        )
        if not isinstance(sort_rule, Anyone):
            msg = f"Can't sort {self.entity.__name__} by {sort_field_name!r}"
            raise UnsortableFieldError(msg)

        masking = self._masking_rules()
        flags = [
            rule.to_sql(self.entity).label(f"_can_read_{name}")
            for name, rule in masking.items()
        ]
        predicates = [
            *self.policy.rows(self.entity, Operation.READ),
            *(gate(f, self.entity, self.policy) for f in filters or ()),
        ]

        stmt = select(self.entity, *flags).where(
            *(p.to_sql(self.entity) for p in predicates)
        )

        decoded_cursor = None

        if cursor is not None:
            decoded_cursor = Cursor.decode(cursor)
            # Validate cursor matches requested sort parameters
            if (
                decoded_cursor.sort_field != sort_field_name
                or decoded_cursor.sort_order != sort_order
            ):
                msg = (
                    f"Cursor sort parameters "
                    f"(field='{decoded_cursor.sort_field}', "
                    f"order='{decoded_cursor.sort_order.value}') do not match "
                    f"requested parameters (field='{sort_field_name}', "
                    f"order='{sort_order.value}')"
                )
                raise ValueError(msg)

            sort_column = getattr(self.entity, sort_field_name)
            if sort_order == SortOrder.ASC:
                stmt = stmt.where(
                    (sort_column > decoded_cursor.sort_value)
                    | (
                        (sort_column == decoded_cursor.sort_value)
                        & (self.entity.uid > decoded_cursor.uid)
                    )
                )
            else:
                stmt = stmt.where(
                    (sort_column < decoded_cursor.sort_value)
                    | (
                        (sort_column == decoded_cursor.sort_value)
                        & (self.entity.uid > decoded_cursor.uid)
                    )
                )

        sort_column = getattr(self.entity, sort_field_name)
        order_func = asc if sort_order == SortOrder.ASC else desc
        stmt = stmt.order_by(order_func(sort_column), asc(self.entity.uid)).limit(
            page_size + 1
        )

        results = [
            self._stamp(row[0], dict(zip(masking, row[1:], strict=True)))
            for row in self._db.execute(stmt).all()
        ]

        has_next = len(results) > page_size
        items = results[:page_size]
        has_previous = cursor is not None and len(items) > 0

        previous_cursor = None
        if has_previous:
            first_item = items[0]
            sort_value = getattr(first_item, sort_field_name)
            previous_cursor = Cursor(
                sort_value=sort_value,
                uid=str(first_item.uid),
                sort_field=sort_field_name,
                sort_order=sort_order,
            ).encode()

        next_cursor = None
        if has_next and items:
            last_item = items[-1]
            sort_value = getattr(last_item, sort_field_name)
            next_cursor = Cursor(
                sort_value=sort_value,
                uid=str(last_item.uid),
                sort_field=sort_field_name,
                sort_order=sort_order,
            ).encode()

        return PaginatedResult(
            items=items,
            previous_cursor=previous_cursor,
            next_cursor=next_cursor,
            has_previous=has_previous,
            has_next=has_next,
        )

    def get_all(
        self,
        page_size: int = settings.DEFAULT_PAGE_SIZE,
        cursor: str | None = None,
        sort_field: InstrumentedAttribute[Any] | None = None,
        sort_order: SortOrder = SortOrder.ASC,
    ) -> PaginatedResult[T]:
        """Get every row the policy allows, paginated. See ``get_filtered``."""
        return self.get_filtered(
            filters=None,
            page_size=page_size,
            cursor=cursor,
            sort_field=sort_field,
            sort_order=sort_order,
        )

    def find_by_uid(self, uid: str) -> T | None:
        """Return the row with ``uid`` if the policy lets the viewer see it."""
        result = self.get_filtered([Equals(field="uid", value=uid)], page_size=1)
        return result.items[0] if result.items else None

    def _check_create(self, obj: T) -> None:
        for guard in self.policy.rows(self.entity, Operation.CREATE):
            if not guard.is_satisfied_by(obj):
                msg = (
                    f"{type(obj).__name__} instance rejected by write guard "
                    f"{type(guard).__name__}"
                )
                raise NotAuthorisedError(msg)

    def create(self, obj: T) -> T:
        """Insert ``obj`` after checking the policy's CREATE guards.

        Guards are judged against the in-memory instance (there is no row yet
        to attach a WHERE to). Child objects attached through a cascading
        relationship (e.g. ``Upload.statuses``) are inserted with it, under
        the parent's guard. Flushes so an ``IntegrityError`` surfaces here;
        does not commit.

        Raises:
            NotAuthorisedError: If any guard rejects the instance.
        """
        self._check_create(obj)
        self._db.add(obj)
        self._db.flush()
        return obj

    def create_many(self, objs: Sequence[T]) -> list[T]:
        """Insert every object in ``objs``; all are checked before any is added.

        Raises:
            NotAuthorisedError: If any guard rejects any instance.
        """
        for obj in objs:
            self._check_create(obj)
        self._db.add_all(objs)
        self._db.flush()
        return list(objs)

    def update(
        self,
        uid: str,
        values: Mapping[str, Any],
        where: Sequence[Predicate] = (),
    ) -> T:
        """Atomically update the row with ``uid``, if the policy allows it.

        The policy's UPDATE row rules AND the UPDATE field rule of every key in
        ``values`` (deny by default) ride in the UPDATE's WHERE, so the check
        and the write are one statement. ``where`` adds the caller's own
        conditions (e.g. "not already archived"); like any caller filter they
        are gated against READ visibility. The returned row then goes back to a
        reader, so it is re-masked with the READ field rules. Does not commit.

        Raises:
            NotAuthorisedError: If no row matched ``uid`` and every guard — the
                caller cannot tell "not found" from "not allowed" (by design).
        """
        writable = self.policy.fields(self.entity, Operation.UPDATE)
        guards = [
            *self.policy.rows(self.entity, Operation.UPDATE),
            *(writable.get(field, Nobody()) for field in values),
            *(gate(w, self.entity, self.policy) for w in where),
        ]
        # `populate_existing` so the RETURNING row overwrites any already-loaded
        # identity-map instance; otherwise the returned object would carry stale
        # pre-update attribute values until the next expire/commit.
        stmt = (
            sa_update(self.entity)
            .where(self.entity.uid == uid, *(g.to_sql(self.entity) for g in guards))
            .values(dict(values))
            .returning(self.entity)
            .execution_options(synchronize_session=False, populate_existing=True)
        )
        result = self._db.execute(stmt).scalars().one_or_none()
        if result is None:
            msg = (
                f"No {self.entity.__name__} with uid {uid!r} satisfied the "
                "update guards"
            )
            raise NotAuthorisedError(msg)

        if masking := self._masking_rules():
            flags = self._db.execute(
                select(
                    *(r.to_sql(self.entity).label(n) for n, r in masking.items())
                ).where(self.entity.uid == uid)
            ).one()
            self._stamp(result, dict(zip(masking, flags, strict=True)))
        return result

    def delete(self, uid: str) -> None:
        """Permanently delete the row with ``uid``, if the policy allows it.

        Deleting is treated as the strongest kind of UPDATE: the UPDATE row
        rules ride in the DELETE's WHERE. Does not commit.

        Raises:
            NotAuthorisedError: If no row matched ``uid`` and every guard.
        """
        rules = self.policy.rows(self.entity, Operation.UPDATE)
        stmt = (
            sa_delete(self.entity)
            .where(self.entity.uid == uid, *(r.to_sql(self.entity) for r in rules))
            .returning(self.entity.uid)
            .execution_options(synchronize_session="fetch")
        )
        if self._db.execute(stmt).first() is None:
            msg = f"No {self.entity.__name__} with uid {uid!r} could be deleted"
            raise NotAuthorisedError(msg)
