"""Operation-aware permission predicates for entity access control."""

from enum import StrEnum
from typing import Literal, overload

from src.app.repository import (
    Equals,
    HexClaim,
    HexClaimByCell,
    Or,
    Related,
    Upload,
    UserGroup,
)
from src.app.repository.database import BaseModel
from src.app.repository.models import User
from src.app.repository.predicates import Filter, Guard


class Operation(StrEnum):
    """The kind of access a permission predicate authorizes."""

    READ = "read"
    CREATE = "create"
    UPDATE = "update"


@overload
def permissions_predicates(
    user: User,
    entity: type[BaseModel],
    operation: Literal[Operation.CREATE],
) -> list[Guard]: ...


@overload
def permissions_predicates(
    user: User,
    entity: type[BaseModel],
    operation: Literal[Operation.READ, Operation.UPDATE] = ...,
) -> list[Filter]: ...


def permissions_predicates(
    user: User,
    entity: type[BaseModel],
    operation: Operation = Operation.READ,
) -> list[Filter] | list[Guard]:
    """Return the permission predicates for `operation` on `entity`.

    The operation decides which projection of a predicate the caller needs, and
    the overloads carry that into the return type:

      * READ / UPDATE -> `list[Filter]`: rendered via `to_sql` into a read's
        WHERE (`get_filtered`) or an atomic UPDATE's WHERE (`Repository.update`).
      * CREATE -> `list[Guard]`: evaluated via `is_satisfied_by` against the
        in-memory instance (`Repository.create`), since an INSERT has no row to
        attach a WHERE to.

    Callers get the precise type, so a READ/UPDATE result can't be passed to
    `create(guards=...)`. The implementation below is only checked against the
    union, though: keep CREATE branches to predicates that define
    `is_satisfied_by` (never `Related` / `Or` — a relational policy can't be
    judged against an unpersisted row).

    Args:
        user: The authenticated user.
        entity: The SQLAlchemy model class to authorize against.
        operation: READ (default), CREATE or UPDATE.

    Returns:
        `Filter`s for READ/UPDATE, `Guard`s for CREATE.

    Raises:
        ValueError: If no permission predicates are defined for the entity and
            operation.
    """
    if entity is Upload or entity is HexClaim:
        # Same-row ownership: sound as both a Filter and a Guard.
        return [Equals(field="user_uid", value=user.uid)]

    # A read-only view: readable, but never created or updated.
    if entity is HexClaimByCell and operation is Operation.READ:
        return [Equals(field="user_uid", value=user.uid)]

    if entity is UserGroup:
        is_owner = Equals(field="owner_uid", value=user.uid)
        if operation is Operation.CREATE:
            # A user may only create a group they own.
            return [is_owner]
        if operation is Operation.UPDATE:
            # Only the owner may mutate a group.
            return [is_owner]
        # Readable if the user owns the group or is a member of it.
        return [
            Or(
                predicates=[
                    is_owner,
                    Related(
                        field="members",
                        inner=Equals(field="uid", value=user.uid),
                    ),
                ]
            )
        ]

    msg = f"No {operation} permission predicates defined for {entity.__name__}"
    raise ValueError(msg)
