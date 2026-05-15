"""Service layer for user groups and their memberships."""

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DBSession

from src.app.repository import (
    EqualsFilter,
    Repository,
    User,
    UserGroup,
    UserGroupMembership,
)
from src.app.repository.filters import Filter
from src.app.services.permissions import permission_filters
from src.app.settings import settings
from src.app.utils import PaginatedResult, SortOrder, get_logger

logger = get_logger(__name__)


class UserGroupNotFoundError(Exception):
    """Group not found, archived, or not visible to the requesting user."""


class DuplicateMembershipError(Exception):
    """A membership row already exists for this (user, group) pair."""


def create_group(db: DBSession, owner: User, name: str) -> UserGroup:
    """Create a new group with `owner` as the sole initial member.

    The caller is recorded as the group's owner and automatically gets a
    membership row.
    """
    group = UserGroup(name=name, owner_uid=owner.uid, archived=False)
    db.add(group)
    db.flush()

    membership = UserGroupMembership(
        user_uid=owner.uid,
        user_group_uid=group.uid,
    )
    db.add(membership)
    db.commit()
    db.refresh(group)

    logger.info(
        "user_group_created",
        user_group_uid=group.uid,
        owner_uid=owner.uid,
    )
    return group


def get_group(
    db: DBSession,
    user: User,
    group_uid: str,
    owner_only: bool = False,
) -> UserGroup | None:
    """Return a group if the caller is a member; else None"""
    try:
        return list_groups(
            db,
            user,
            group_uid=group_uid,
            owner_only=owner_only,
        ).items[0]
    except IndexError:
        return None


def list_groups(  # noqa: PLR0913
    db: DBSession,
    user: User,
    page_size: int = settings.DEFAULT_PAGE_SIZE,
    group_uid: str | None = None,
    owner_only: bool = False,
    sort_field: str = "created_at",
    sort_order: SortOrder = SortOrder.DESC,
) -> PaginatedResult[UserGroup]:
    """Return non-archived groups the caller can see."""
    repo = Repository(db, UserGroup)

    filters: list[Filter] = [
        *permission_filters(user, UserGroup),
        EqualsFilter(field="archived", value=False),
    ]

    # FIXME: The below is a permisssion filter, but we can't distinguish
    # between READ permissions and WRITE permissions at the moment.
    # Ideally, we'll have some kind of "operation-aware" permissions system:
    # *permission_filters(user, UserGroup, "UPDATE|DELETE")
    if owner_only:
        filters.append(EqualsFilter(field="owner_uid", value=user.uid))

    if group_uid is not None:
        filters.append(EqualsFilter(field="uid", value=group_uid))

    return repo.get_filtered(
        filters=filters,
        sort_field=getattr(UserGroup, sort_field),
        sort_order=sort_order,
        page_size=page_size,
    )


def update_group(db: DBSession, user: User, group_uid: str, *, name: str) -> UserGroup:
    """Rename a group. Owner-only."""
    group = get_group(db, user, group_uid, owner_only=True)

    if group is None:
        raise UserGroupNotFoundError(group_uid)

    group.name = name
    db.commit()
    db.refresh(group)
    return group


def archive_group(db: DBSession, user: User, group_uid: str) -> UserGroup:
    """Soft-delete a group. Owner-only."""
    group = get_group(db, user, group_uid, owner_only=True)

    if group is None:
        raise UserGroupNotFoundError(group_uid)

    repo = Repository(db, UserGroup)
    repo.delete(group)
    db.commit()
    db.refresh(group)

    logger.info("user_group_archived", user_group_uid=group.uid)
    return group


def list_members(
    db: DBSession, user: User, group_uid: str
) -> list[UserGroupMembership]:
    """Return all memberships of a group the caller belongs to."""
    group = get_group(db, user, group_uid)

    if group is None:
        raise UserGroupNotFoundError(group_uid)

    repo = Repository(db, UserGroupMembership)
    return repo.get_filtered(
        filters=[EqualsFilter(field="user_group_uid", value=group.uid)],
        sort_field=UserGroupMembership.created_at,
        sort_order=SortOrder.ASC,
    ).items


def count_members(db: DBSession, group: UserGroup) -> int:
    """Return the count of memberships for a group.

    Aggregate (`func.count`) — `Repository` doesn't expose `count()`, so
    this stays as raw SQL per the documented exception in CLAUDE.md.
    """
    stmt = select(func.count(UserGroupMembership.uid)).where(
        UserGroupMembership.user_group_uid == group.uid
    )
    return int(db.execute(stmt).scalar_one())


def remove_membership(db: DBSession, user: User, membership_uid: str) -> None:
    """Delete a membership."""
    raise NotImplementedError


def add_member(
    db: DBSession,
    *,
    group: UserGroup,
    user_to_add: User,
) -> UserGroupMembership:
    """Internal helper: add an existing user to a group.

    Not exposed via HTTP — the public flow for adding members will
    arrive with the invitation feature. Kept here as the single point
    at which non-owner membership rows are created so the uniqueness
    handling has one home.
    """
    membership = UserGroupMembership(
        user_uid=user_to_add.uid,
        user_group_uid=group.uid,
    )
    db.add(membership)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        msg = f"User {user_to_add.uid} already a member of {group.uid}"
        raise DuplicateMembershipError(msg) from None
    db.refresh(membership)
    return membership
