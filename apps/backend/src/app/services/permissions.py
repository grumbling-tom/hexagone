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
    db: DBSession,
    user: User,
    target: BaseModel,
) -> set[Capability[ResourceType]]:
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
    caps: set[Capability[ResourceType]] = set()

    # Object-level operations a capability is computed for. CREATE is excluded — it
    # is collection-level (the ``Workspace`` handle), not a property of a row.
    for operation in (Operation.READ, Operation.UPDATE, Operation.DELETE):
        predicates = permissions_predicates(user, entity, operation)
        # READ is implied by presence: ``target`` was returned by a permissioned
        # query, so the user can read it — no need to re-check.
        if operation is Operation.READ:
            caps.add(Capability(operation, resource))
            continue
        if predicates_hold(db, target, predicates):
            caps.add(Capability(operation, resource))
    return caps


def predicates_hold(db: DBSession, target: BaseModel, predicates: list[Filter]) -> bool:
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


def with_capabilities[S: Resource](  # noqa: PLR0913
    schema: type[S],
    obj: BaseModel,
    *,
    user: User,
    db: DBSession,
    target: BaseModel | None = None,
    context: dict[str, Any] | None = None,
) -> S:
    """Serialize ``obj`` into ``schema`` and attach the caller's capabilities.

    Args:
        schema: The response schema to build (a ``Resource`` subclass).
        obj: The ORM instance to read the response fields from.
        user: The authenticated caller.
        db: Database session (for relational capability checks).
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
    resp.capabilities = sorted(capabilities_for(db, user, target or obj))
    return resp
