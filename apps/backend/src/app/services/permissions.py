"""Permission filters for entity access control."""

from src.app.repository import EqualsFilter, HexClaim, HexClaimByCell, Upload
from src.app.repository.database import BaseModel
from src.app.repository.filters import Filter
from src.app.repository.models import User


def permission_filters(user: User, entity: type[BaseModel]) -> list[Filter]:
    """Return query filters that restrict access to entities owned by the user.

    Args:
        user: The authenticated user.
        entity: The SQLAlchemy model class to filter.

    Returns:
        List of filters to apply to queries.

    Raises:
        ValueError: If no permission filters are defined for the entity.
    """
    if entity is Upload or entity is HexClaim or entity is HexClaimByCell:
        return [EqualsFilter(field="user_uid", value=user.uid)]

    msg = f"No permission filters defined for {entity.__name__}"
    raise ValueError(msg)
