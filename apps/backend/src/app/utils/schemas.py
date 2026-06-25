from abc import abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from typing import Any
from typing_extensions import Self

from pydantic import BaseModel, ConfigDict, Field


class BaseSchema(BaseModel):
    """Base class for all Pydantic schemas in the project.

    Provides common configuration for all Pydantic schemas to distinguish them
    from SQLAlchemy's BaseModel. All request/response schemas should inherit
    from this class.
    """

    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True,
    )


class Operation(StrEnum):
    """The verb half of a capability — the kind of access being authorized."""

    READ = "read"
    UPDATE = "update"  # update-in-place of an existing row (was WRITE)
    CREATE = "create"
    DELETE = "delete"  # not yet enforced; here so capabilities can report it


@dataclass(frozen=True, slots=True, order=True)
class Capability[T]:
    """A permission the current user holds: the ``(Operation, T)`` product.

    Frozen + ordered so capabilities can live in a ``set`` and be ``sorted`` for
    a stable wire order. The verb (``operation``) names *what kind* of access;
    the noun (``resource``) names *what it is about*.
    """

    operation: Operation
    resource: T


class Resource[T](BaseSchema):
    """Base for any response that describes a uniquely addressable resource.

    Carries ``capabilities`` — what the caller may do with this resource (a
    concrete instance, or, via the ``WORKSPACE`` handle, what they may create).
    The ``Capability`` value object is used directly as the wire type; it is the
    same ``(operation, resource)`` information the rest of the system uses.

    NOT a universal response base — only schemas describing one addressable
    resource inherit it; wrappers like ``PaginatedResult`` do not.
    """

    uid: str
    capabilities: list[Capability[T]] = Field(default=[])
