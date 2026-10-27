"""Predicate schemas for generic repository filtering and write guards.

A predicate is a small Pydantic value object that expresses a single condition.
It is consumed in one of two ways, decided entirely by the CALL SITE:

  1. narrow a read query / guard an atomic UPDATE — via ``to_sql``, which renders
     the predicate to a SQLAlchemy boolean expression. Every predicate supports
     this; it is the only universally-required capability.
  2. guard an INSERT — via ``is_satisfied_by``, an in-memory check. Defined ONLY
     on predicates that can be evaluated against a single instance. Predicates
     whose meaning depends on related rows (``Related`` -> EXISTS) or on other
     predicates that may themselves be SQL-only (``Or``) deliberately omit it.

These two capabilities are expressed as two structural ``typing.Protocol``s,
``Filter`` and ``Guard``, used ONLY as parameter annotations on repository
methods. The concrete hierarchy keeps a nominal base, ``Predicate``, because a
Protocol cannot serve as a Pydantic field type for nested construction
(``Or.filters``, ``Related.inner``).

The discriminator is method *presence*, not behaviour: ``Predicate`` declares
only ``to_sql``, never ``is_satisfied_by``. Adding a raising ``is_satisfied_by``
stub "for completeness" would silently re-admit ``Or``/``Related`` as create
guards — don't.
"""

import re
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from pydantic import Field
from sqlalchemy import ColumnElement, and_, false, or_, true

from ..utils import BaseSchema

if TYPE_CHECKING:
    from .database import BaseModel


@runtime_checkable
class Filter(Protocol):
    """Renders to a SQL boolean expression.

    Usable to narrow reads (``get_filtered``) OR to guard an atomic UPDATE — the
    predicate becomes part of the ``WHERE`` clause either way.
    """

    def to_sql(self, entity: type[BaseModel]) -> ColumnElement[bool]: ...


@runtime_checkable
class Guard(Protocol):
    """Evaluable against an in-memory instance.

    Usable to guard an INSERT, where there is no persisted row to attach a
    ``WHERE`` to.
    """

    def is_satisfied_by(self, obj: BaseModel) -> bool: ...


class Predicate(BaseSchema, ABC):
    """Nominal base for all concrete predicates (Pydantic nesting + SQL contract).

    Declares only the universal ``to_sql`` contract. It is the type used for
    nested fields (``list[Predicate]``, ``Predicate``) so Pydantic can
    construct nested predicate trees.

    It carries no ``field``: a combinator (``And``/``Or``), a relationship hop
    (``Related``) and a constant (``Anyone``/``Nobody``) don't name a column,
    and ``gate()`` relies on ``FieldPredicate`` meaning exactly "a leaf that
    reads one column".

    NOTE: there is intentionally no ``is_satisfied_by`` here — its absence is the
    structural discriminator that keeps SQL-only predicates out of
    ``create(guards=...)``.
    """

    @abstractmethod
    def to_sql(self, entity: type[BaseModel]) -> ColumnElement[bool]:
        """Render this predicate to a SQLAlchemy boolean expression."""


class FieldPredicate(Predicate, ABC):
    """A leaf predicate that reads exactly one column, named by ``field``."""

    field: str = Field(
        ..., description="Name of the model field the predicate refers to"
    )


class Equals[T](FieldPredicate):
    """Exact equality comparison.

    Example:
        Equals(field="archived", value=False)  # archived = False
    """

    value: T = Field(..., description="Value to compare for equality")

    def to_sql(self, entity: type[BaseModel]) -> ColumnElement[bool]:
        return getattr(entity, self.field) == self.value

    def is_satisfied_by(self, obj: BaseModel) -> bool:
        return bool(getattr(obj, self.field) == self.value)


class NotEquals[T](FieldPredicate):
    """Inequality comparison.

    Example:
        NotEquals(field="status", value="deleted")  # status != 'deleted'
    """

    value: T = Field(..., description="Value to compare for inequality")

    def to_sql(self, entity: type[BaseModel]) -> ColumnElement[bool]:
        return getattr(entity, self.field) != self.value

    def is_satisfied_by(self, obj: BaseModel) -> bool:
        return bool(getattr(obj, self.field) != self.value)


class GreaterThan[T](FieldPredicate):
    """Greater-than comparison.

    Example:
        GreaterThan(field="price", value=100)  # price > 100
    """

    value: T = Field(..., description="Value for greater than comparison")

    def to_sql(self, entity: type[BaseModel]) -> ColumnElement[bool]:
        return getattr(entity, self.field) > self.value

    def is_satisfied_by(self, obj: BaseModel) -> bool:
        return bool(getattr(obj, self.field) > self.value)


class GreaterThanOrEqual[T](FieldPredicate):
    """Greater-than-or-equal comparison.

    Example:
        GreaterThanOrEqual(field="age", value=18)  # age >= 18
    """

    value: T = Field(..., description="Value for greater than or equal comparison")

    def to_sql(self, entity: type[BaseModel]) -> ColumnElement[bool]:
        return getattr(entity, self.field) >= self.value

    def is_satisfied_by(self, obj: BaseModel) -> bool:
        return bool(getattr(obj, self.field) >= self.value)


class LessThan[T](FieldPredicate):
    """Less-than comparison.

    Example:
        LessThan(field="stock", value=10)  # stock < 10
    """

    value: T = Field(..., description="Value for less than comparison")

    def to_sql(self, entity: type[BaseModel]) -> ColumnElement[bool]:
        return getattr(entity, self.field) < self.value

    def is_satisfied_by(self, obj: BaseModel) -> bool:
        return bool(getattr(obj, self.field) < self.value)


class LessThanOrEqual[T](FieldPredicate):
    """Less-than-or-equal comparison.

    Example:
        LessThanOrEqual(field="capacity", value=50)  # capacity <= 50
    """

    value: T = Field(..., description="Value for less than or equal comparison")

    def to_sql(self, entity: type[BaseModel]) -> ColumnElement[bool]:
        return getattr(entity, self.field) <= self.value

    def is_satisfied_by(self, obj: BaseModel) -> bool:
        return bool(getattr(obj, self.field) <= self.value)


class Like(FieldPredicate):
    """SQL LIKE pattern matching (case-insensitive by default).

    Example:
        Like(field="name", pattern="%test%")  # name ILIKE '%test%'
    """

    pattern: str = Field(..., description="SQL LIKE pattern with % wildcards")
    case_sensitive: bool = Field(
        default=False, description="Whether pattern matching is case-sensitive"
    )

    def to_sql(self, entity: type[BaseModel]) -> ColumnElement[bool]:
        column = getattr(entity, self.field)
        if self.case_sensitive:
            return column.like(self.pattern)
        return column.ilike(self.pattern)

    def is_satisfied_by(self, obj: BaseModel) -> bool:
        value = getattr(obj, self.field)
        if value is None:
            return False
        # Translate the SQL LIKE pattern to a regex: `%` -> any run, `_` -> any
        # single char. re.escape leaves `_` literal but escapes `%` to `\%`.
        regex = re.escape(self.pattern).replace(r"\%", ".*").replace("_", ".")
        flags = 0 if self.case_sensitive else re.IGNORECASE
        # NOTE: Python regex matching can diverge from the database's LIKE
        # collation; the two projections must agree for guard use to be sound.
        return re.fullmatch(regex, str(value), flags) is not None


class In[T](FieldPredicate):
    """SQL IN — value is one of an allowed set.

    Example:
        In(field="status", values=["active", "pending"])  # status IN (...)
    """

    values: list[T] = Field(..., description="List of allowed values")

    def to_sql(self, entity: type[BaseModel]) -> ColumnElement[bool]:
        return getattr(entity, self.field).in_(self.values)

    def is_satisfied_by(self, obj: BaseModel) -> bool:
        return getattr(obj, self.field) in self.values


class NotIn[T](FieldPredicate):
    """SQL NOT IN — value is none of an excluded set.

    Example:
        NotIn(field="status", values=["deleted", "archived"])  # status NOT IN (...)
    """

    values: list[T] = Field(..., description="List of excluded values")

    def to_sql(self, entity: type[BaseModel]) -> ColumnElement[bool]:
        return ~getattr(entity, self.field).in_(self.values)

    def is_satisfied_by(self, obj: BaseModel) -> bool:
        return getattr(obj, self.field) not in self.values


class Range[T](FieldPredicate):
    """Range query between inclusive min/max bounds; either may be None.

    Example:
        Range(field="created_at", min_value=start, max_value=end)
        # created_at >= start AND created_at <= end
    """

    min_value: T | None = Field(
        default=None, description="Minimum value (inclusive), None for no lower bound"
    )
    max_value: T | None = Field(
        default=None, description="Maximum value (inclusive), None for no upper bound"
    )

    def to_sql(self, entity: type[BaseModel]) -> ColumnElement[bool]:
        column = getattr(entity, self.field)
        conditions: list[ColumnElement[bool]] = []
        if self.min_value is not None:
            conditions.append(column >= self.min_value)
        if self.max_value is not None:
            conditions.append(column <= self.max_value)
        if not conditions:
            return true()
        return and_(*conditions)

    def is_satisfied_by(self, obj: BaseModel) -> bool:
        value = getattr(obj, self.field)
        if self.min_value is not None and value < self.min_value:
            return False
        return not (self.max_value is not None and value > self.max_value)


class IsNull(FieldPredicate):
    """NULL / NOT NULL check.

    Example:
        IsNull(field="deleted_at", is_null=True)  # deleted_at IS NULL
    """

    is_null: bool = Field(
        default=True, description="True to filter for NULL, False for NOT NULL"
    )

    def to_sql(self, entity: type[BaseModel]) -> ColumnElement[bool]:
        column = getattr(entity, self.field)
        if self.is_null:
            return column.is_(None)
        return column.is_not(None)

    def is_satisfied_by(self, obj: BaseModel) -> bool:
        return (getattr(obj, self.field) is None) == self.is_null


class Or(Predicate):
    """OR-compose any number of inner predicates into a single boolean expression.

    The ``predicates`` list is typed as the nominal ``Predicate`` so Pydantic
    can nest arbitrary predicates (including SQL-only ones like ``Related``).

    Example:
        Or(predicates=[
            Equals(field="status", value="active"),
            Equals(field="status", value="pending"),
        ])
        # (status = 'active') OR (status = 'pending')
    """

    predicates: list[Predicate] = Field(
        ...,
        description="Inner predicates whose SQL expressions are OR-combined",
    )

    def to_sql(self, entity: type[BaseModel]) -> ColumnElement[bool]:
        if not self.predicates:
            return false()  # an empty OR matches nothing
        return or_(*(p.to_sql(entity) for p in self.predicates))

    # No is_satisfied_by: an OR whose children may be SQL-only can't be evaluated
    # in memory. Omitting it makes `Or` a static type error as a create guard.


class And(Predicate):
    """AND-compose any number of inner predicates into a single expression.

    Mostly built by ``gate()`` to pin a caller's leaf to its field's
    visibility rule; callers can use it too. Like ``Or`` it has no
    ``is_satisfied_by``, because its children may be SQL-only.

    Example:
        And(predicates=[
            Equals(field="email", value="bob@acme.com"),
            Equals(field="archived", value=False),
        ])
    """

    predicates: list[Predicate] = Field(
        ...,
        description="Inner predicates whose SQL expressions are AND-combined",
    )

    def to_sql(self, entity: type[BaseModel]) -> ColumnElement[bool]:
        if not self.predicates:
            return true()  # an empty AND matches everything
        return and_(*(p.to_sql(entity) for p in self.predicates))


class Anyone(Predicate):
    """Always true. As a rule: every viewer may do this to every row/field."""

    def to_sql(self, entity: type[BaseModel]) -> ColumnElement[bool]:  # noqa: ARG002
        return true()

    def is_satisfied_by(self, obj: BaseModel) -> bool:  # noqa: ARG002
        return True


class Nobody(Predicate):
    """Always false. The deny-by-default rule for anything not granted."""

    def to_sql(self, entity: type[BaseModel]) -> ColumnElement[bool]:  # noqa: ARG002
        return false()

    def is_satisfied_by(self, obj: BaseModel) -> bool:  # noqa: ARG002
        return False


class Related(Predicate):
    """Filter rows whose named relationship contains a row satisfying an inner
    predicate, via ``EXISTS`` (``.any()`` for to-many, ``.has()`` for to-one).

    ``field`` is the name of a relationship attribute on the outer entity;
    ``inner`` is interpreted against the related entity's class.

    Example:
        # Uploads with at least one status of UPLOAD_SUCCESS
        Related(
            field="statuses",
            inner=Equals(field="status", value="UPLOAD_SUCCESS"),
        )
    """

    field: str = Field(
        ..., description="Name of the relationship attribute on the outer entity"
    )
    inner: Predicate = Field(
        ..., description="Predicate to apply against the related entity"
    )

    def to_sql(self, entity: type[BaseModel]) -> ColumnElement[bool]:
        relationship_attr = getattr(entity, self.field)
        target_class = relationship_attr.property.mapper.class_
        condition = self.inner.to_sql(target_class)
        # `.any()` for to-many (uselist=True), `.has()` for to-one.
        if relationship_attr.property.uselist:
            return relationship_attr.any(condition)
        return relationship_attr.has(condition)

    # Omitting is_satisfied_by on Related is correct, but the precise
    # justification is: a create guard runs against an unpersisted instance
    # whose relationships aren't loaded, so the only sound way to evaluate a
    # relational predicate is a query — and a Guard is defined as the thing
    # that doesn't query. Relational authorization therefore belongs on the
    # read side (which is exactly what add_member's get_group(..., UPDATE)
    # does), and the type system encoding "Related can't be a create guard"
    # matches that reality.
