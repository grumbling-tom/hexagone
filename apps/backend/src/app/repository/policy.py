"""The ``Policy`` seam between the repository and the permission rules.

A ``ScopedRepository`` can't be built without a ``Policy``, and a ``Policy``
answers exactly two questions about an entity for an operation:

  * ``rows``   — which rows? (predicates ANDed into the WHERE, or, for CREATE,
    guards checked against the in-memory instance)
  * ``fields`` — which parts of a row? (one predicate per field, evaluated per
    row as a boolean column for READ, or ANDed into the WHERE for UPDATE)

The protocol lives in the repository layer so the repository can depend on it;
the rules for a real viewer (``ViewerPolicy``) live in ``services/permissions``.
``SystemPolicy`` lives here because it needs no rules at all.
"""

from collections.abc import Mapping, Sequence
from enum import StrEnum
from typing import Literal, Protocol, overload

from sqlalchemy import inspect
from sqlalchemy.ext.hybrid import HybridExtensionType

from .database import BaseModel
from .predicates import Anyone, Guard, Predicate


class Operation(StrEnum):
    """The kind of access a permission predicate authorizes."""

    READ = "read"
    CREATE = "create"
    UPDATE = "update"


type FieldRules = Mapping[str, Predicate]


class Policy(Protocol):
    """The permission rules for one viewer, consulted by ``ScopedRepository``.

    ``rows`` is overloaded like ``row_rules``: CREATE yields ``Guard``s (judged
    in memory against the instance being inserted), READ/UPDATE yield
    ``Predicate``s (rendered into a WHERE). Without the overloads here,
    ``ScopedRepository.create`` couldn't call ``is_satisfied_by`` — which is
    the point: ``Predicate`` deliberately doesn't have it.
    """

    @overload
    def rows(
        self, entity: type[BaseModel], operation: Literal[Operation.CREATE]
    ) -> Sequence[Guard]: ...

    @overload
    def rows(
        self,
        entity: type[BaseModel],
        operation: Literal[Operation.READ, Operation.UPDATE],
    ) -> Sequence[Predicate]: ...

    def fields(
        self,
        entity: type[BaseModel],
        operation: Literal[Operation.READ, Operation.UPDATE],
    ) -> FieldRules:
        """Return one rule per field; a missing field means ``Nobody()``."""
        ...


class SystemPolicy:
    """Unrestricted. For code with no viewer: sign-in, sessions, workers.

    Every use should be easy to find in a search — ``grep SystemPolicy`` is the
    audit list of places that see everything.
    """

    def rows(
        self,
        entity: type[BaseModel],  # noqa: ARG002
        operation: Operation,  # noqa: ARG002
    ) -> Sequence[Anyone]:
        """Every row, for every operation."""
        return [Anyone()]

    def fields(
        self,
        entity: type[BaseModel],
        operation: Operation,  # noqa: ARG002
    ) -> FieldRules:
        """Every column and hybrid property, for every operation."""
        return {name: Anyone() for name in queryable_fields(entity)}


def queryable_fields(entity: type[BaseModel]) -> list[str]:
    """Names a predicate can test: columns plus public hybrid properties.

    Hybrids (``Upload.current_status``) are filterable but aren't columns, so
    a rule set built from columns alone gates their filters to ``Nobody()``.
    """
    mapper = inspect(entity)
    hybrids = [
        key
        for key, attr in mapper.all_orm_descriptors.items()
        if attr.extension_type is HybridExtensionType.HYBRID_PROPERTY
        and not key.startswith("_")
    ]
    return [c.key for c in mapper.column_attrs] + hybrids
