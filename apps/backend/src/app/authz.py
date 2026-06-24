"""Surfacing capabilities to the frontend.

The wire contract for "what may the current user do here": every response that
describes a single resource carries a ``capabilities`` list — the structured
``Capability`` product (``(operation, resource)``), never a stringly-typed
scope. The FE reads it to gate affordances (show Edit only if
``(update, user_group)`` is present).

This lives at the app layer (above ``services``) so the serializer can depend on
``services.permissions`` without inverting the ``utils -> services`` direction.
"""

from typing import Any

from pydantic import Field
from sqlalchemy.orm import Session as DBSession

from src.app.repository.database import BaseModel
from src.app.repository.models import User
from src.app.services.permissions import Capability, capabilities_for
from src.app.utils import BaseSchema


def _no_capabilities() -> list[Capability]:
    """Typed default factory for the ``capabilities`` field (empty by default)."""
    return []


class Resource(BaseSchema):
    """Base for any response that describes a single addressable resource.

    Carries ``capabilities`` — what the caller may do with this resource (a
    concrete instance, or, via the ``WORKSPACE`` handle, what they may create).
    The ``Capability`` value object is used directly as the wire type; it is the
    same ``(operation, resource)`` information the rest of the system uses.

    NOT a universal response base — only schemas describing one addressable
    resource inherit it; wrappers like ``PaginatedResult`` do not.
    """

    uid: str
    capabilities: list[Capability] = Field(default_factory=_no_capabilities)


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


__all__ = ["Resource", "with_capabilities"]
