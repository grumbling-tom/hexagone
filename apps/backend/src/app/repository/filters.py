"""Filter schemas for generic repository filtering.

Provides type-safe filter classes that can be used with the Repository pattern
to build dynamic queries from user input. All filters inherit from BaseSchema
and implement the apply() method to convert themselves to SQLAlchemy WHERE clauses.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from pydantic import Field
from sqlalchemy import or_
from sqlalchemy import select as sa_select

from ..utils import BaseSchema

if TYPE_CHECKING:
    from sqlalchemy import Select

    from .database import BaseModel


class Filter(BaseSchema, ABC):
    """Base class for all filter schemas.

    All concrete filter classes must implement the apply() method to convert
    the filter into a SQLAlchemy WHERE clause.

    Attributes:
        field: The name of the model field to filter on.
    """

    field: str = Field(..., description="Name of the model field to filter on")

    @abstractmethod
    def apply(
        self, stmt: Select[tuple[Any, ...]], entity: type[BaseModel]
    ) -> Select[tuple[Any, ...]]:
        """Apply this filter to a SQLAlchemy select statement.

        Args:
            stmt: The select statement to modify.
            entity: The entity class being queried.

        Returns:
            Modified select statement with filter applied.
        """


class EqualsFilter[T](Filter):
    """Filter for exact equality comparison.

    Attributes:
            field: The field name to filter on.
            value: The value to compare for equality.

        Example:
            EqualsFilter(field="archived", value=False)
            # Generates: WHERE archived = False
    """

    value: T = Field(..., description="Value to compare for equality")

    def apply(
        self, stmt: Select[tuple[Any, ...]], entity: type[BaseModel]
    ) -> Select[tuple[Any, ...]]:
        """Apply equality filter to the statement."""
        column = getattr(entity, self.field)
        return stmt.where(column == self.value)


class NotEqualsFilter[T](Filter):
    """Filter for inequality comparison.

    Attributes:
        field: The field name to filter on.
        value: The value to compare for inequality.

    Example:
        NotEqualsFilter(field="status", value="deleted")
        # Generates: WHERE status != 'deleted'
    """

    value: T = Field(..., description="Value to compare for inequality")

    def apply(
        self, stmt: Select[tuple[Any, ...]], entity: type[BaseModel]
    ) -> Select[tuple[Any, ...]]:
        """Apply inequality filter to the statement."""
        column = getattr(entity, self.field)
        return stmt.where(column != self.value)


class GreaterThanFilter[T](Filter):
    """Filter for greater than comparison.

    Attributes:
        field: The field name to filter on.
        value: The value to compare against.

    Example:
        GreaterThanFilter(field="price", value=100)
        # Generates: WHERE price > 100
    """

    value: T = Field(..., description="Value for greater than comparison")

    def apply(
        self, stmt: Select[tuple[Any, ...]], entity: type[BaseModel]
    ) -> Select[tuple[Any, ...]]:
        """Apply greater than filter to the statement."""
        column = getattr(entity, self.field)
        return stmt.where(column > self.value)


class GreaterThanOrEqualFilter[T](Filter):
    """Filter for greater than or equal comparison.

    Attributes:
        field: The field name to filter on.
        value: The value to compare against.

    Example:
        GreaterThanOrEqualFilter(field="age", value=18)
        # Generates: WHERE age >= 18
    """

    value: T = Field(..., description="Value for greater than or equal comparison")

    def apply(
        self, stmt: Select[tuple[Any, ...]], entity: type[BaseModel]
    ) -> Select[tuple[Any, ...]]:
        """Apply greater than or equal filter to the statement."""
        column = getattr(entity, self.field)
        return stmt.where(column >= self.value)


class LessThanFilter[T](Filter):
    """Filter for less than comparison.

    Attributes:
        field: The field name to filter on.
        value: The value to compare against.

    Example:
        LessThanFilter(field="stock", value=10)
        # Generates: WHERE stock < 10
    """

    value: T = Field(..., description="Value for less than comparison")

    def apply(
        self, stmt: Select[tuple[Any, ...]], entity: type[BaseModel]
    ) -> Select[tuple[Any, ...]]:
        """Apply less than filter to the statement."""
        column = getattr(entity, self.field)
        return stmt.where(column < self.value)


class LessThanOrEqualFilter[T](Filter):
    """Filter for less than or equal comparison.

    Attributes:
        field: The field name to filter on.
        value: The value to compare against.

    Example:
        LessThanOrEqualFilter(field="capacity", value=50)
        # Generates: WHERE capacity <= 50
    """

    value: T = Field(..., description="Value for less than or equal comparison")

    def apply(
        self, stmt: Select[tuple[Any, ...]], entity: type[BaseModel]
    ) -> Select[tuple[Any, ...]]:
        """Apply less than or equal filter to the statement."""
        column = getattr(entity, self.field)
        return stmt.where(column <= self.value)


class LikeFilter(Filter):
    """Filter for SQL LIKE pattern matching.

    Supports both case-sensitive and case-insensitive pattern matching.

    Attributes:
        field: The field name to filter on.
        pattern: SQL LIKE pattern (use % for wildcards).
        case_sensitive: Whether the match should be case-sensitive.

    Example:
        LikeFilter(field="name", pattern="%test%", case_sensitive=False)
        # Generates: WHERE name ILIKE '%test%'
    """

    pattern: str = Field(..., description="SQL LIKE pattern with % wildcards")
    case_sensitive: bool = Field(
        default=False, description="Whether pattern matching is case-sensitive"
    )

    def apply(
        self, stmt: Select[tuple[Any, ...]], entity: type[BaseModel]
    ) -> Select[tuple[Any, ...]]:
        """Apply LIKE filter to the statement."""
        column = getattr(entity, self.field)
        if self.case_sensitive:
            return stmt.where(column.like(self.pattern))
        return stmt.where(column.ilike(self.pattern))


class InFilter[T](Filter):
    """Filter for SQL IN operator.

    Checks if the field value is in a list of allowed values.

    Attributes:
        field: The field name to filter on.
        values: List of allowed values.

    Example:
        InFilter(field="status", values=["active", "pending"])
        # Generates: WHERE status IN ('active', 'pending')
    """

    values: list[T] = Field(..., description="List of allowed values")

    def apply(
        self, stmt: Select[tuple[Any, ...]], entity: type[BaseModel]
    ) -> Select[tuple[Any, ...]]:
        """Apply IN filter to the statement."""
        column = getattr(entity, self.field)
        return stmt.where(column.in_(self.values))


class NotInFilter[T](Filter):
    """Filter for SQL NOT IN operator.

    Checks if the field value is not in a list of excluded values.

    Attributes:
        field: The field name to filter on.
        values: List of excluded values.

    Example:
        NotInFilter(field="status", values=["deleted", "archived"])
        # Generates: WHERE status NOT IN ('deleted', 'archived')
    """

    values: list[T] = Field(..., description="List of excluded values")

    def apply(
        self, stmt: Select[tuple[Any, ...]], entity: type[BaseModel]
    ) -> Select[tuple[Any, ...]]:
        """Apply NOT IN filter to the statement."""
        column = getattr(entity, self.field)
        return stmt.where(~column.in_(self.values))


class RangeFilter[T](Filter):
    """Filter for range queries between minimum and maximum values.

    Either min_value or max_value can be None to create an open-ended range.

    Attributes:
        field: The field name to filter on.
        min_value: Minimum value (inclusive), None for no lower bound.
        max_value: Maximum value (inclusive), None for no upper bound.

    Example:
        RangeFilter(
            field="created_at",
            min_value=datetime(2024, 1, 1),
            max_value=datetime(2024, 12, 31)
        )
        # Generates: WHERE created_at >= '2024-01-01' AND created_at <= '2024-12-31'
    """

    min_value: T | None = Field(
        default=None, description="Minimum value (inclusive), None for no lower bound"
    )
    max_value: T | None = Field(
        default=None, description="Maximum value (inclusive), None for no upper bound"
    )

    def apply(
        self, stmt: Select[tuple[Any, ...]], entity: type[BaseModel]
    ) -> Select[tuple[Any, ...]]:
        """Apply range filter to the statement."""
        column = getattr(entity, self.field)
        if self.min_value is not None:
            stmt = stmt.where(column >= self.min_value)
        if self.max_value is not None:
            stmt = stmt.where(column <= self.max_value)
        return stmt


class IsNullFilter(Filter):
    """Filter for NULL checks.

    Checks if a field is NULL or NOT NULL.

    Attributes:
        field: The field name to filter on.
        is_null: True to filter for NULL values, False for NOT NULL.

    Example:
        IsNullFilter(field="deleted_at", is_null=True)
        # Generates: WHERE deleted_at IS NULL
    """

    is_null: bool = Field(
        default=True, description="True to filter for NULL, False for NOT NULL"
    )

    def apply(
        self, stmt: Select[tuple[Any, ...]], entity: type[BaseModel]
    ) -> Select[tuple[Any, ...]]:
        """Apply NULL check filter to the statement."""
        column = getattr(entity, self.field)
        if self.is_null:
            return stmt.where(column.is_(None))
        return stmt.where(column.is_not(None))


class OrFilter(Filter):
    """OR-compose any number of inner Filters into a single WHERE clause.

    `field` is inherited from ``Filter`` but unused by ``OrFilter``; it
    defaults to ``""`` so the model can be constructed without one. The
    real contract is the ``filters`` list of inner Filter instances.

    Empty ``filters`` is a no-op (returns the statement unchanged). With
    one filter it's equivalent to applying that filter directly. With two
    or more, the inner WHERE clauses are OR-combined via SQLAlchemy
    ``or_``. Filters that build multiple conditions internally (e.g.
    ``RangeFilter`` with both bounds → ``(col >= min) AND (col <= max)``)
    flow through naturally — their combined boolean expression is what
    gets OR'd at this level.

    Example:
        OrFilter(filters=[
            EqualsFilter(field="status", value="active"),
            EqualsFilter(field="status", value="pending"),
        ])
        # Generates: WHERE (status = 'active') OR (status = 'pending')
    """

    field: str = ""  # Hack to satisfy base class, not used by OrFilter
    filters: list[Filter] = Field(
        ...,
        description="Inner Filter instances whose WHERE clauses are OR-combined",
    )

    def apply(
        self, stmt: Select[tuple[Any, ...]], entity: type[BaseModel]
    ) -> Select[tuple[Any, ...]]:
        """Apply the OR of all inner filters to the statement."""
        if not self.filters:
            return stmt
        clauses: list[Any] = []
        for inner in self.filters:
            applied = inner.apply(sa_select(entity), entity)
            if applied.whereclause is not None:
                clauses.append(applied.whereclause)
        if not clauses:
            return stmt
        return stmt.where(or_(*clauses))


class RelationFilter(Filter):
    """Filter rows whose named SQLAlchemy relationship contains a row
    satisfying an inner Filter.

    ``field`` is the name of a relationship attribute on the outer entity
    (to-many or to-one). ``inner`` is any Filter, interpreted against the
    related entity's class. The composite SQL is
    ``EXISTS (SELECT 1 FROM <related> WHERE <inner>)``, produced via
    SQLAlchemy's ``.any()`` for collection relationships or ``.has()``
    for scalar (to-one) relationships.

    The inner filter is run against a fresh ``select(<related entity>)``
    and its WHERE clause is extracted via ``Select.whereclause`` — the same
    trick ``OrFilter`` uses — so any Filter can be the inner, including
    ``OrFilter``, ``InFilter``, or another ``RelationFilter`` for
    multi-hop traversal.

    Example:
        # Uploads with at least one status of UPLOAD_SUCCESS
        RelationFilter(
            field="statuses",
            inner=EqualsFilter(field="status", value="UPLOAD_SUCCESS"),
        )
    """

    field: str = Field(
        ..., description="Name of the relationship attribute on the outer entity"
    )
    inner: Filter = Field(..., description="Filter to apply against the related entity")

    def apply(
        self, stmt: Select[tuple[Any, ...]], entity: type[BaseModel]
    ) -> Select[tuple[Any, ...]]:
        """Wrap the inner filter's condition in EXISTS over the relationship."""
        relationship_attr = getattr(entity, self.field)
        target_class = relationship_attr.property.mapper.class_
        applied = self.inner.apply(sa_select(target_class), target_class)
        condition = applied.whereclause
        if condition is None:
            return stmt
        # `.any()` for to-many (uselist=True), `.has()` for to-one.
        op = (
            relationship_attr.any
            if relationship_attr.property.uselist
            else relationship_attr.has
        )
        return stmt.where(op(condition))
