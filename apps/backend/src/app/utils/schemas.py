from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    PlainSerializer,
    PlainValidator,
    WithJsonSchema,
)

from src.app.utils.redaction import Redacted


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


def _only_the_marker(value: object) -> Redacted:
    if value is not Redacted.REDACTED:
        msg = "not the REDACTED marker"
        raise ValueError(msg)
    return value


# Accepts only the in-memory ``REDACTED`` marker and serialises it as
# ``{"redacted": true}``. The validator is a plain function (not the enum
# itself) so the marker contributes exactly the one schema written here.
RedactedMarker = Annotated[
    Redacted,
    PlainValidator(_only_the_marker),
    PlainSerializer(lambda _: {"redacted": True}, when_used="json"),
    WithJsonSchema(
        {
            "title": "Redacted",
            "type": "object",
            "properties": {"redacted": {"type": "boolean", "enum": [True]}},
            "required": ["redacted"],
        }
    ),
]

type Redactable[T] = T | RedactedMarker
