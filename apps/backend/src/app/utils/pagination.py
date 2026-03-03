from pydantic import computed_field

from .schemas import BaseSchema


class PaginatedResult[T](BaseSchema):
    """Wrapper for paginated query results with cursor-based pagination.

    Provides cursor-based pagination metadata along with the result items.
    Cursors are opaque base64-encoded strings that capture pagination state
    including sort field, sort order, and position for stable, consistent
    pagination.

    Type parameter:
        T: The type of items in the result list

    Attributes:
        items: The list of result items for the current page.
        previous_cursor: Opaque cursor string for the first item on this
            page, None if first page.
        next_cursor: Opaque cursor string for fetching the next page, None
            if no more pages.
        has_previous: Whether there are items before this page.
        has_next: Whether there are more items after this page.
        page_size: Number of items requested per page.
    """

    items: list[T]
    previous_cursor: str | None
    next_cursor: str | None
    has_previous: bool
    has_next: bool

    @computed_field
    def page_size(self) -> int:
        """Number of items returned in this page.

        Returns:
            The length of the items list.
        """
        return len(self.items)
