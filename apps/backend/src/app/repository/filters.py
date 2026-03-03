"""Filter schemas for generic repository filtering.

Provides type-safe filter classes that can be used with the Repository pattern
to build dynamic queries from user input. All filters inherit from BaseSchema
and implement the apply() method to convert themselves to SQLAlchemy WHERE clauses.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from pydantic import Field

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
