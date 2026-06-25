"""Operation-aware permission predicates for entity access control."""

from enum import StrEnum

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
from src.app.repository.predicates import Filter


class Operation(StrEnum):
    """The kind of access a permission predicate authorizes."""

    READ = "read"
    WRITE = "write"


def permissions_predicates(
    user: User,
    entity: type[BaseModel],
    operation: Operation = Operation.READ,
) -> list[Filter]:
    """Return predicates that narrow queries / guard atomic updates for `entity`.

    Return type is `list[Filter]`: every permission predicate renders to SQL, so
    these feed `get_filtered` and the atomic `Repository.update`. They are NOT
    typed as `Guard` and so cannot be splatted into `create(guards=...)` —
    feeding insert guards from permissions would require a separate
    `Guard`-typed accessor (which has no answer for relational policies).

    Args:
        user: The authenticated user.
        entity: The SQLAlchemy model class to authorize against.
        operation: READ (default) or WRITE; lets a single entity expose a
            narrower predicate for mutations than for reads.

    Returns:
        List of `Filter` predicates to apply to queries / update guards.

    Raises:
        ValueError: If no permission predicates are defined for the entity.
    """
    if entity is Upload or entity is HexClaim or entity is HexClaimByCell:
        return [Equals(field="user_uid", value=user.uid)]

    if entity is UserGroup:
        is_owner = Equals(field="owner_uid", value=user.uid)
        if operation is Operation.WRITE:
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

    msg = f"No permission predicates defined for {entity.__name__}"
    raise ValueError(msg)
