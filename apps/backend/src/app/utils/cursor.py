import base64
import json
from enum import Enum
from typing import Any

from src.app.utils.schemas import BaseSchema


class SortOrder(Enum):
    """Sort order enumeration for pagination.

    Provides ASC and DESC values for sorting, with support for negation
    to flip the sort order.

    Attributes:
        ASC: Ascending sort order.
        DESC: Descending sort order.
    """

    ASC = "asc"
    DESC = "desc"

    def __neg__(self) -> SortOrder:
        """Return the opposite sort order.

        Returns:
            DESC if this is ASC, ASC if this is DESC.
        """
        return SortOrder.ASC if self == SortOrder.DESC else SortOrder.DESC


class Cursor(BaseSchema):
    """Represents a pagination cursor with sort information.

    Encodes pagination state including the last item's sort field value,
    UID, and sort order. The cursor is base64-encoded to make it opaque
    to clients.

    Attributes:
        sort_value: The value of the sort field for the last item on the page.
        uid: The UID of the last item on the page.
        sort_field: The field name used for sorting.
        sort_order: The sort order (SortOrder.ASC or SortOrder.DESC).
    """

    sort_value: Any
    uid: str
    sort_field: str
    sort_order: SortOrder

    def encode(self) -> str:
        """Encode the cursor to a base64-encoded JSON string.

        Returns:
            Base64-encoded string representing the cursor state.
        """
        cursor_dict = {
            "sort_value": self.sort_value,
            "uid": self.uid,
            "sort_field": self.sort_field,
            "sort_order": self.sort_order.value,
        }
        json_str = json.dumps(cursor_dict, default=str)
        return base64.b64encode(json_str.encode()).decode()

    @classmethod
    def decode(cls, encoded_cursor: str) -> Cursor:
        """Decode a base64-encoded cursor string.

        Args:
            encoded_cursor: Base64-encoded cursor string.

        Returns:
            Decoded Cursor instance.

        Raises:
            ValueError: If the cursor cannot be decoded or is malformed.
        """
        try:
            json_str = base64.b64decode(encoded_cursor.encode()).decode()
            cursor_dict = json.loads(json_str)
            return cls(
                sort_value=cursor_dict["sort_value"],
                uid=cursor_dict["uid"],
                sort_field=cursor_dict["sort_field"],
                sort_order=SortOrder(cursor_dict["sort_order"]),
            )
        except (KeyError, json.JSONDecodeError, ValueError) as e:
            msg = f"Invalid cursor format: {e}"
            raise ValueError(msg) from e
