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

from typing import Any

from src.app.repository import (
    Equals,
    Guard,
    HexClaim,
    HexClaimByCell,
    Or,
    Related,
    ResourceType,
    Upload,
    UserGroup,
)
from src.app.repository.database import BaseModel
from src.app.repository.models import User
from src.app.repository.predicates import Filter
from src.app.services.workspace import Workspace
from src.app.utils import Capability, Operation, Resource


def permissions_predicates(
    user: User,
    entity: type[BaseModel],
    operation: Operation = Operation.READ,
) -> list[Filter]:
    if entity in (Upload, HexClaim, HexClaimByCell) and operation in (
        Operation.READ,
        Operation.UPDATE,
    ):
        return [Equals(field="user_uid", value=user.uid)]

    if entity is UserGroup:
        is_owner = Equals(field="owner_uid", value=user.uid)

        if operation is Operation.UPDATE:
            return [is_owner]

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

    msg = f"No permission predicates defined for {operation} on {entity.__name__}"
    raise ValueError(msg)


def capabilities_for(
    user: User,
    target: BaseModel,
) -> set[Capability[ResourceType]]:
    """The capabilities ``user`` holds on ``target``.

    ``target`` is either an entity instance (object-level READ/UPDATE/DELETE) or
    the ``WORKSPACE`` handle (collection-level CREATE). Returns the same
    ``set[Capability]`` shape for both, so callers (and the FE) need one type.

    Computed purely in memory, no DB session required. This rests on a single
    load-bearing assumption: **if we hold an ORM object in memory, we have read
    access to it.** We assume every ``target`` came from a permission-filtered
    query, so its mere presence proves READ — there is nothing to re-check. The
    remaining (write) operations are gated by owner-style ``Guard`` predicates,
    which are field comparisons on the row itself, so they too need no query.
    """
    if isinstance(target, Workspace):
        return {
            Capability(Operation.CREATE, entity.__resource__)
            for entity in Workspace.CREATABLE
            if Workspace.permits_create(user, entity)
        }

    entity = type(target)
    resource = entity.__resource__
    caps: set[Capability[ResourceType]] = set()

    # Object-level operations a capability is computed for. CREATE is excluded — it
    # is collection-level (the ``Workspace`` handle), not a property of a row.
    for operation in (Operation.READ, Operation.UPDATE, Operation.DELETE):
        predicates = permissions_predicates(user, entity, operation)
        # READ is implied by presence (see the assumption above): ``target`` was
        # returned by a permission-filtered query, so the user can read it.
        if operation is Operation.READ:
            caps.add(Capability(operation, resource))
            continue
        if predicates_hold(target, predicates):
            caps.add(Capability(operation, resource))

    return caps


def predicates_hold(target: BaseModel, predicates: list[Filter]) -> bool:
    """Whether ``predicates`` hold for ``target``, evaluated in memory.

    Write-side capabilities are gated by owner-style ``Guard`` predicates (a
    single ``Equals`` against a column already loaded on ``target``), so they
    evaluate with no query. Relational predicates (``Or``/``Related``) only ever
    gate READ, which is answered by presence and never reaches here — so a
    non-``Guard`` predicate at this point breaks the invariant and we fail loud
    rather than silently mis-grant a capability.
    """
    guards = [p for p in predicates if isinstance(p, Guard)]
    if len(guards) != len(predicates):
        msg = (
            "Capability predicates must be in-memory Guards; got a relational "
            f"predicate for {type(target).__name__}. Relational rules can gate "
            "reads (answered by presence) but not writes."
        )
        raise ValueError(msg)
    return all(guard.is_satisfied_by(target) for guard in guards)


def with_capabilities[S: Resource](
    schema: type[S],
    obj: BaseModel,
    *,
    user: User,
    target: BaseModel | None = None,
    context: dict[str, Any] | None = None,
) -> S:
    """Serialize ``obj`` into ``schema`` and attach the caller's capabilities.

    Args:
        schema: The response schema to build (a ``Resource`` subclass).
        obj: The ORM instance to read the response fields from.
        user: The authenticated caller.
        target: The object whose capabilities to report, when it differs from
            ``obj`` — e.g. ``/users/current`` serializes the ``User`` but reports
            collection-level capabilities against the ``WORKSPACE`` handle.
            Defaults to ``obj`` (the common object-level case).
        context: Optional pydantic validation context (e.g. ``{"storage": ...}``
            for ``UploadResponse``'s presigned-URL resolution).

    Returns:
        The populated response with its ``capabilities`` sorted for a stable
        wire order.
    """
    resp = schema.model_validate(obj, context=context)
    resp.capabilities = sorted(capabilities_for(user, target or obj))
    return resp
