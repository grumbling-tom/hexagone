from typing import TYPE_CHECKING, Any

from sqlalchemy import asc, desc, select
from sqlalchemy import update as sa_update

from ..settings import settings
from ..utils import Cursor, PaginatedResult, SortOrder
from .database import BaseModel
from .predicates import Equals, Filter, Guard, Range

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from datetime import datetime

    from sqlalchemy.orm import InstrumentedAttribute, Session


class NotAuthorisedError(Exception):
    """A write guard rejected an in-memory instance before it was persisted."""


class Repository[T: BaseModel]:
    """Generic repository pattern for database access.

    Provides common database operations for any SQLAlchemy model type using
    SQLAlchemy 2.0 select syntax. All query methods return PaginatedResult
    objects with cursor-based pagination and support custom sorting. Cursors
    are opaque base64-encoded strings that capture pagination state including
    sort parameters. Works with models that may have optional fields like
    archived, created_by, updated_by, and created_at.

    Type parameter:
        T: The SQLAlchemy model class type
    """

    def __init__(self, db: Session, entity: type[T]) -> None:
        """Initialize repository with a database session and entity type.

        Args:
            db: SQLAlchemy session
            entity: The SQLAlchemy model class
        """
        self.db = db
        self.entity = entity

    def get_filtered(
        self,
        filters: Sequence[Filter] | None = None,
        page_size: int = settings.DEFAULT_PAGE_SIZE,
        cursor: str | None = None,
        sort_field: InstrumentedAttribute[Any] | None = None,
        sort_order: SortOrder = SortOrder.ASC,
    ) -> PaginatedResult[T]:
        """Get entities with optional filters, pagination, and custom sorting.

        Provides a flexible filtering mechanism using type-safe Filter schemas.
        This is the core query method that other convenience methods delegate to.

        Args:
            filters: List of Filter objects to apply to the query.
            page_size: Number of items per page. Defaults to DEFAULT_PAGE_SIZE
                from settings.
            cursor: Opaque cursor string for fetching the next page, None for
                first page.
            sort_field: SQLAlchemy column attribute to sort by. If None, defaults
                to the entity's uid column.
            sort_order: Sort order (default: SortOrder.ASC).

        Returns:
            Paginated result containing items and pagination metadata.

        Raises:
            ValueError: If cursor is malformed or cursor sort parameters don't
                match requested parameters.
        """
        # Default to uid column if no sort_field provided
        if sort_field is None:
            sort_field = self.entity.uid

        sort_field_name = sort_field.name

        stmt = select(self.entity)

        # Apply filters
        if filters:
            for predicate in filters:
                stmt = stmt.where(predicate.to_sql(self.entity))

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

        results = list(self.db.execute(stmt).scalars().all())

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
        """Get all entities with cursor-based pagination and custom sorting.

        Args:
            page_size: Number of items per page. Defaults to DEFAULT_PAGE_SIZE
                from settings.
            cursor: Opaque cursor string for fetching the next page, None for
                first page.
            sort_field: SQLAlchemy column attribute to sort by. If None, defaults
                to the entity's uid column.
            sort_order: Sort order (default: SortOrder.ASC).

        Returns:
            Paginated result containing items and pagination metadata.

        Raises:
            ValueError: If cursor is malformed.
        """
        return self.get_filtered(
            filters=None,
            page_size=page_size,
            cursor=cursor,
            sort_field=sort_field,
            sort_order=sort_order,
        )

    def get_by_uid(self, uid: str) -> T:
        """Get entity by UID, raises exception if not found.

        Args:
            uid: UID string value

        Returns:
            The entity instance

        Raises:
            NoResultFound: If no entity with the given UID exists
        """
        stmt = select(self.entity).where(self.entity.uid == uid)
        return self.db.execute(stmt).scalar_one()

    def find_by_uid(self, uid: str) -> T | None:
        """Find entity by UID, returns None if not found.

        Args:
            uid: UID string value

        Returns:
            The entity instance or None if not found
        """
        stmt = select(self.entity).where(self.entity.uid == uid)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_actives(
        self,
        page_size: int = settings.DEFAULT_PAGE_SIZE,
        cursor: str | None = None,
        sort_field: InstrumentedAttribute[Any] | None = None,
        sort_order: SortOrder = SortOrder.ASC,
    ) -> PaginatedResult[T]:
        """Get all active entities with cursor-based pagination and custom sorting.

        Only works with entities that have an archived field.

        Args:
            page_size: Number of items per page. Defaults to DEFAULT_PAGE_SIZE
                from settings.
            cursor: Opaque cursor string for fetching the next page, None for
                first page.
            sort_field: SQLAlchemy column attribute to sort by. If None, defaults
                to the entity's uid column.
            sort_order: Sort order (default: SortOrder.ASC).

        Returns:
            Paginated result containing active items and pagination metadata.

        Raises:
            ValueError: If cursor is malformed.
        """
        return self.get_filtered(
            filters=[Equals(field="archived", value=False)],
            page_size=page_size,
            cursor=cursor,
            sort_field=sort_field,
            sort_order=sort_order,
        )

    def get_by_create_datetime_range(  # noqa: PLR0913
        self,
        from_datetime: datetime,
        to_datetime: datetime,
        page_size: int = settings.DEFAULT_PAGE_SIZE,
        cursor: str | None = None,
        sort_field: InstrumentedAttribute[Any] | None = None,
        sort_order: SortOrder = SortOrder.ASC,
    ) -> PaginatedResult[T]:
        """Get entities within a datetime range with pagination and sorting.

        Works with the created_at field from BaseModel.

        Args:
            from_datetime: Start of datetime range (inclusive).
            to_datetime: End of datetime range (inclusive).
            page_size: Number of items per page. Defaults to DEFAULT_PAGE_SIZE
                from settings.
            cursor: Opaque cursor string for fetching the next page, None for
                first page.
            sort_field: SQLAlchemy column attribute to sort by. If None, defaults
                to the entity's uid column.
            sort_order: Sort order (default: SortOrder.ASC).

        Returns:
            Paginated result containing items and pagination metadata.

        Raises:
            ValueError: If cursor is malformed.
        """
        return self.get_filtered(
            filters=[
                Range(
                    field="created_at",
                    min_value=from_datetime,
                    max_value=to_datetime,
                )
            ],
            page_size=page_size,
            cursor=cursor,
            sort_field=sort_field,
            sort_order=sort_order,
        )

    def add(self, entity: T, created_by_user_id: int | None = None) -> None:
        """Add a new entity to the database.

        If the entity has a created_by field, it will be set to created_by_user_id.
        Does not commit the transaction.

        Args:
            entity: The entity instance to add
            created_by_user_id: Optional user ID who created this entity
        """
        if created_by_user_id is not None and hasattr(entity, "created_by"):
            entity.created_by = created_by_user_id  # pyright: ignore
        self.db.add(entity)

    def create(self, obj: T, guards: Sequence[Guard] = ()) -> T:
        """Insert a new entity after checking in-memory write guards.

        Each guard is a `Guard` predicate evaluated against the instance being
        inserted (there is no persisted row yet to attach a WHERE to). The first
        guard that the instance does not satisfy raises `NotAuthorisedError`.
        Flushes so an `IntegrityError` surfaces here; does not commit.

        Args:
            obj: The entity instance to insert.
            guards: In-memory predicates the instance must satisfy.

        Returns:
            The inserted (flushed) entity.

        Raises:
            NotAuthorisedError: If any guard rejects the instance.
        """
        for guard in guards:
            if not guard.is_satisfied_by(obj):
                msg = (
                    f"{type(obj).__name__} instance rejected by write guard "
                    f"{type(guard).__name__}"
                )
                raise NotAuthorisedError(msg)
        self.db.add(obj)
        self.db.flush()
        return obj

    def update(
        self,
        uid: str,
        values: Mapping[str, Any],
        guards: Sequence[Filter] = (),
    ) -> T:
        """Atomically update the row with `uid`, gated by SQL write guards.

        Each guard is a `Filter` predicate rendered into the UPDATE's WHERE
        clause, so the permission/invariant check and the mutation happen in a
        single statement (no check-then-act race). Raises `NotAuthorisedError`
        if no row matched `uid` AND every guard — the caller cannot tell
        "not found" from "guard failed" (403-vs-404 collapse, by design).
        Does not commit.

        Args:
            uid: UID of the row to update.
            values: Column/value mapping to set.
            guards: SQL predicates that must hold for the update to apply.

        Returns:
            The updated entity.

        Raises:
            NotAuthorisedError: If no row matched `uid` and every guard.
        """
        stmt = sa_update(self.entity).where(self.entity.uid == uid)
        for guard in guards:
            stmt = stmt.where(guard.to_sql(self.entity))
        # `populate_existing` so the RETURNING row overwrites any already-loaded
        # identity-map instance; otherwise the returned object would carry stale
        # pre-update attribute values until the next expire/commit.
        stmt = (
            stmt.values(dict(values))
            .returning(self.entity)
            .execution_options(synchronize_session=False, populate_existing=True)
        )
        result = self.db.execute(stmt).scalars().one_or_none()
        if result is None:
            msg = (
                f"No {self.entity.__name__} with uid {uid!r} satisfied the "
                "update guards"
            )
            raise NotAuthorisedError(msg)
        return result

    def delete(self, entity: T, deleted_by_user_id: int | None = None) -> None:
        """Soft delete an entity by setting archived to True.

        Only works with entities that have an archived field.
        Does not commit the transaction.

        Args:
            entity: The entity instance to delete
            deleted_by_user_id: Optional user ID who deleted this entity
        """
        if hasattr(entity, "archived"):
            entity.archived = True  # pyright: ignore
        if deleted_by_user_id is not None and hasattr(entity, "updated_by"):
            entity.updated_by = deleted_by_user_id  # pyright: ignore

    def permanent_delete(self, entity: T) -> None:
        """Permanently delete an entity from the database.

        Does not commit the transaction.

        Args:
            entity: The entity instance to permanently delete
        """
        self.db.delete(entity)
