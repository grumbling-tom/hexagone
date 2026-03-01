from pydantic import BaseModel, ConfigDict


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
