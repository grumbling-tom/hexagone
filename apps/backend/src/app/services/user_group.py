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
from src.app.services.permissions import permission_filters
from src.app.utils import SortOrder, get_logger

logger = get_logger(__name__)


class UserGroupNotFoundError(Exception):
    """Group not found, archived, or not visible to the requesting user."""


class UserGroupMembershipNotFoundError(Exception):
    """Membership not found or not accessible to the requesting user."""


class NotGroupOwnerError(Exception):
    """Action requires the requesting user to be the group's owner."""


class SoleOwnerCannotLeaveError(Exception):
    """Sole owner of a group with other members cannot leave; archive instead."""


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


def list_groups_for_user(db: DBSession, user: User) -> list[UserGroup]:
    """Return non-archived groups the caller can see."""
    repo = Repository(db, UserGroup)
    return repo.get_filtered(
        filters=[
            *permission_filters(user, UserGroup),
            EqualsFilter(field="archived", value=False),
        ],
        sort_field=UserGroup.created_at,
        sort_order=SortOrder.DESC,
    ).items


def update_group(db: DBSession, user: User, group_uid: str, *, name: str) -> UserGroup:
    """Rename a group. Owner-only."""
    repo = Repository(db, UserGroup)
    group = repo.get_filtered(
        filters=[
            EqualsFilter(field="uid", value=group_uid),
            EqualsFilter(field="archived", value=False),
            # FIXME: The below is a permisssion filter, but we can't distinguish
            # between READ permissions and WRITE permissions at the moment.
            # Ideally, we'll have some kind of "operation-aware" permissions system:
            # *permission_filters(user, UserGroup, "UPDATE"),
            EqualsFilter(field="owner_uid", value=user.uid),
        ],
        page_size=1,
    )
    if not group.items:
        raise UserGroupNotFoundError(group_uid)

    group = group.items[0]

    group.name = name
    db.commit()
    db.refresh(group)
    return group


def archive_group(db: DBSession, user: User, group_uid: str) -> UserGroup:
    """Soft-delete a group. Owner-only."""
    repo = Repository(db, UserGroup)
    group = repo.get_filtered(
        filters=[
            EqualsFilter(field="uid", value=group_uid),
            EqualsFilter(field="archived", value=False),
            # FIXME: The below is a permisssion filter, but we can't distinguish
            # between READ permissions and WRITE permissions at the moment.
            # Ideally, we'll have some kind of "operation-aware" permissions system:
            # *permission_filters(user, UserGroup, "DELETE"),
            EqualsFilter(field="owner_uid", value=user.uid),
        ],
        page_size=1,
    )
    if not group.items:
        raise UserGroupNotFoundError(group_uid)

    group = group.items[0]

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
    repo = Repository(db, UserGroup)
    result = repo.get_filtered(
        filters=[
            *permission_filters(user, UserGroup),
            EqualsFilter(field="uid", value=group_uid),
            EqualsFilter(field="archived", value=False),
        ],
        page_size=1,
    )

    if not result.items:
        raise UserGroupNotFoundError(group_uid)

    group = result.items[0]

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


def _load_membership_for_access(
    db: DBSession, user: User, membership_uid: str
) -> tuple[UserGroupMembership, UserGroup]:
    """Load (membership, its group) if the caller is the member or the owner.

    Two ``Repository.find_by_uid`` calls rather than a single multi-entity
    select — keeps the service raw-SQL-free at the cost of one extra
    round-trip on a non-hot path. Archived parent groups are treated as
    "not found" (404) so existence isn't leaked.
    """
    membership = Repository(db, UserGroupMembership).find_by_uid(membership_uid)
    if membership is None:
        raise UserGroupMembershipNotFoundError(membership_uid)

    group = Repository(db, UserGroup).find_by_uid(membership.user_group_uid)
    if group is None or group.archived:
        raise UserGroupMembershipNotFoundError(membership_uid)

    is_self = membership.user_uid == user.uid
    is_owner = group.owner_uid == user.uid
    if not (is_self or is_owner):
        # Don't leak existence of memberships in groups the caller can't see.
        raise UserGroupMembershipNotFoundError(membership_uid)
    return membership, group


def remove_membership(db: DBSession, user: User, membership_uid: str) -> None:
    """Delete a membership. Allowed for self-leave or owner-kick.

    Rejects with SoleOwnerCannotLeaveError if the owner tries to leave a
    group with other members. The owner can only leave by archiving the
    group instead.
    """
    membership, group = _load_membership_for_access(db, user, membership_uid)

    if membership.user_uid == group.owner_uid:
        # Owner is being removed. Allowed only if they are the sole member;
        # otherwise the group would be orphaned.
        member_count = count_members(db, group)
        if member_count > 1:
            raise SoleOwnerCannotLeaveError(group.uid)

    db.delete(membership)
    db.commit()

    logger.info(
        "user_group_membership_removed",
        membership_uid=membership_uid,
        user_group_uid=group.uid,
    )


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
