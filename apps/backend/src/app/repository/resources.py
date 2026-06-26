"""The set of real resource types the system understands and authorizes against.

A ``ResourceType`` is the object half of a ``Capability`` (the ``(operation,
resource)`` pair in ``services/permissions.py``) — the honest, enumerated
counterpart to a fake noun like ``admin``. Each addressable/creatable model maps
to one via its ``__resource__`` classvar (declared on ``BaseModel``, set on each
model), so the capability machinery can name *what* a permission is about without
stringly-typing it.

This module is dependency-free on purpose: ``database.py`` (which declares the
``__resource__`` annotation on ``BaseModel``) imports from here, so it must sit
below the rest of the repository.
"""

from enum import StrEnum


class ResourceType(StrEnum):
    """A kind of resource the system authorizes against."""

    USER = "user"
    USER_GROUP = "user_group"
    UPLOAD = "upload"
