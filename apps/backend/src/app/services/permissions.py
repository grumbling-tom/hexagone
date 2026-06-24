"""Operation-aware permissions: predicates, and the capability product.

Two questions, one mechanism:

  * **Object-level** ("which operations may this user perform on *this* row?") —
    answered by evaluating an operation's predicates against a fetched instance.
    These are the genuinely relational, instance-varying rules (owner vs member
    of a particular group).
  * **Collection-level** ("what may this user create?") — has no instance, so it
    is answered against the table-less ``Workspace`` handle (see
    ``services/workspace.py``).

``capabilities_for`` unifies both: pass an entity instance OR the ``WORKSPACE``
singleton, get back a ``set[Capability]`` either way. A ``Capability`` is the
honest ``(Operation, ResourceType)`` product — the verb *and* the real noun.
"""

from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy.orm import Session as DBSession

from src.app.repository import (
    Equals,
    Guard,
    HexClaim,
    HexClaimByCell,
    Or,
    Related,
    Repository,
    ResourceType,
    Upload,
    UserGroup,
)
from src.app.repository.database import BaseModel
from src.app.repository.models import User
from src.app.repository.predicates import Filter
from src.app.services.workspace import Workspace


class Operation(StrEnum):
    """The verb half of a capability — the kind of access being authorized."""

    READ = "read"
    UPDATE = "update"  # update-in-place of an existing row (was WRITE)
    CREATE = "create"
    DELETE = "delete"  # not yet enforced; here so capabilities can report it


# Object-level operations a capability is computed for. CREATE is excluded — it
# is collection-level (the ``Workspace`` handle), not a property of a row.
_OBJECT_OPERATIONS = (Operation.READ, Operation.UPDATE, Operation.DELETE)


@dataclass(frozen=True, slots=True, order=True)
class Capability:
    """A permission the current user holds: the ``(Operation, ResourceType)`` product.

    Frozen + ordered so capabilities can live in a ``set`` and be ``sorted`` for
    a stable wire order. The verb (``operation``) names *what kind* of access;
    the noun (``resource``) names *what it is about*.
    """

    operation: Operation
    resource: ResourceType


def permissions_predicates(
    user: User,
    entity: type[BaseModel],
    operation: Operation = Operation.READ,
) -> list[Filter] | None:
    """Predicates that authorize ``operation`` on ``entity`` for ``user``.

    Return values:
        * ``None`` — the operation is not defined for this entity (e.g. DELETE),
          i.e. nobody holds it. Distinct from ``[]`` (unconditionally allowed).
        * ``[p, ...]`` — allowed where every predicate holds. Each renders to SQL
          (the ``Filter`` protocol), so the list feeds ``get_filtered`` and the
          atomic ``Repository.update``.

    Raises:
        ValueError: If no permission policy is defined for the entity at all.
    """
    if entity is Upload or entity is HexClaim or entity is HexClaimByCell:
        if operation in (Operation.READ, Operation.UPDATE):
            return [Equals(field="user_uid", value=user.uid)]
        return None

    if entity is UserGroup:
        is_owner = Equals(field="owner_uid", value=user.uid)
        if operation is Operation.READ:
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
        if operation is Operation.UPDATE:
            # Only the owner may mutate a group.
            return [is_owner]
        return None

    msg = f"No permission predicates defined for {entity.__name__}"
    raise ValueError(msg)


def required_predicates(
    user: User,
    entity: type[BaseModel],
    operation: Operation = Operation.READ,
) -> list[Filter]:
    """``permissions_predicates`` for callers that require the operation to exist.

    Query filtering and update guards address a specific, known operation; a
    ``None`` there is a programming error, not "no access". This narrows the
    nullable policy to a concrete ``list[Filter]``, raising if the operation is
    not defined for the entity.
    """
    predicates = permissions_predicates(user, entity, operation)
    if predicates is None:
        msg = f"{operation} is not a permitted operation on {entity.__name__}"
        raise ValueError(msg)
    return predicates


def capabilities_for(
    db: DBSession,
    user: User,
    target: BaseModel,
) -> set[Capability]:
    """The capabilities ``user`` holds on ``target``.

    ``target`` is either an entity instance (object-level READ/UPDATE/DELETE) or
    the ``WORKSPACE`` handle (collection-level CREATE). Returns the same
    ``set[Capability]`` shape for both, so callers (and the FE) need one type.
    """
    if isinstance(target, Workspace):
        return {
            Capability(Operation.CREATE, entity.__resource__)
            for entity in Workspace.CREATABLE
            if Workspace.permits_create(user, entity)
        }

    entity = type(target)
    resource = entity.__resource__
    caps: set[Capability] = set()
    for operation in _OBJECT_OPERATIONS:
        predicates = permissions_predicates(user, entity, operation)
        if predicates is None:
            continue
        # READ is implied by presence: ``target`` was returned by a permissioned
        # query, so the user can read it — no need to re-check.
        if operation is Operation.READ:
            caps.add(Capability(operation, resource))
            continue
        if predicates_hold(db, target, predicates):
            caps.add(Capability(operation, resource))
    return caps


def predicates_hold(
    db: DBSession, target: BaseModel, predicates: list[Filter]
) -> bool:
    """Whether ``predicates`` hold for ``target``.

    In-memory when every predicate is a ``Guard`` (the common case — owner
    checks are a single ``Equals``, so a list page evaluates with no query).
    Falls back to one ``SELECT ... LIMIT 1`` re-query for relational predicates
    (``Or``/``Related``), whose truth depends on other rows.
    """
    guards = [p for p in predicates if isinstance(p, Guard)]
    if len(guards) == len(predicates):
        return all(guard.is_satisfied_by(target) for guard in guards)

    result = Repository(db, type(target)).get_filtered(
        filters=[*predicates, Equals(field="uid", value=target.uid)],
        page_size=1,
    )
    return bool(result.items)
