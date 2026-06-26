from dataclasses import dataclass
from enum import StrEnum

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

    READ = "read"
    UPDATE = "update"
    CREATE = "create"
    DELETE = "delete"


class AuthZNoun(StrEnum):
    # TODO: Explain why this thing exists, and why it exists here.
    UPLOAD = "upload"
    USER_GROUP = "userGroup"


@dataclass(frozen=True, slots=True, order=True)
class Capability:

    operation: Operation
    resource: AuthZNoun


# class Resource[T](BaseSchema):
class Resource(BaseSchema):

    uid: str
    capabilities: list[Capability]


    # @model_validator(mode="wrap")
    # @classmethod
    # def attach_capabilities(
    #     cls,
    #     object: T,
    #     handler: Callable[..., UploadResponse],
    #     info: ValidationInfo,
    # ) -> UploadResponse:
    #     instance = handler(object)

    #     context: dict[str, Any] = info.context or {}
    #     user: User | None = context.get("user")

    #     if user is None:
    #         msg = f"{cls.__name__}.model_validate requires a 'user' in context"
    #         raise ValueError(msg)

    #     instance.capabilities = sorted(capabilities_for(user, object))
    #     return instance

# Potential YAGNI, but suspect we might want to return a 'Workspace'
# singleton resource.
# Since the purpose of `uid` is to distinguish between sibling
# resources, and a singleton has none, we'd be better to omit it,
# rather than insert a fictitious `uid`.
class SingletonResource(BaseSchema):

    capabilities: list[Capability] = Field(default=[])
