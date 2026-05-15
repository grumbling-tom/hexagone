"""Service layer for user groups and their memberships."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DBSession

from src.app.repository import (
    Repository,
    User,
    UserGroup,
    UserGroupMembership,
)
from src.app.utils import get_logger

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


def _get_visible_group(
    db: DBSession, user: User, group_uid: str
) -> tuple[UserGroup, UserGroupMembership]:
    """Return (group, caller's membership) or raise UserGroupNotFoundError.

    A group is visible only if it is not archived and the caller has a
    membership row. Non-members get 404, not 403 — we don't leak the
    existence of groups.
    """
    stmt = (
        select(UserGroup, UserGroupMembership)
        .join(
            UserGroupMembership,
            UserGroupMembership.user_group_uid == UserGroup.uid,
        )
        .where(UserGroup.uid == group_uid)
        .where(UserGroup.archived.is_(False))
        .where(UserGroupMembership.user_uid == user.uid)
    )
    row = db.execute(stmt).one_or_none()
    if row is None:
        raise UserGroupNotFoundError(group_uid)
    return row[0], row[1]


def _assert_is_owner(group: UserGroup, user: User) -> None:
    if group.owner_uid != user.uid:
        raise NotGroupOwnerError(group.uid)


def create_group(db: DBSession, owner: User, name: str) -> UserGroup:
    """Create a new group with `owner` as the sole initial member.

    The caller is recorded as the group's owner and automatically gets a
    membership row with `invited_by_uid=NULL`.
    """
    group = UserGroup(name=name, owner_uid=owner.uid, archived=False)
    db.add(group)
    db.flush()

    membership = UserGroupMembership(
        user_uid=owner.uid,
        user_group_uid=group.uid,
        invited_by_uid=None,
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
    """Return non-archived groups the caller is a member of, newest first."""
    stmt = (
        select(UserGroup)
        .join(
            UserGroupMembership,
            UserGroupMembership.user_group_uid == UserGroup.uid,
        )
        .where(UserGroupMembership.user_uid == user.uid)
        .where(UserGroup.archived.is_(False))
        .order_by(UserGroup.created_at.desc(), UserGroup.uid.asc())
    )
    return list(db.execute(stmt).scalars().all())


def get_group(db: DBSession, user: User, group_uid: str) -> UserGroup:
    """Return a group the caller is a member of, or raise UserGroupNotFoundError."""
    group, _ = _get_visible_group(db, user, group_uid)
    return group


def update_group(db: DBSession, user: User, group_uid: str, *, name: str) -> UserGroup:
    """Rename a group. Owner-only."""
    group, _ = _get_visible_group(db, user, group_uid)
    _assert_is_owner(group, user)

    group.name = name
    db.commit()
    db.refresh(group)
    return group


def archive_group(db: DBSession, user: User, group_uid: str) -> UserGroup:
    """Soft-delete a group. Owner-only."""
    group, _ = _get_visible_group(db, user, group_uid)
    _assert_is_owner(group, user)

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
    group, _ = _get_visible_group(db, user, group_uid)
    stmt = (
        select(UserGroupMembership)
        .where(UserGroupMembership.user_group_uid == group.uid)
        .order_by(UserGroupMembership.created_at.asc(), UserGroupMembership.uid.asc())
    )
    return list(db.execute(stmt).scalars().all())


def count_members(db: DBSession, group: UserGroup) -> int:
    """Return the count of memberships for a group."""
    from sqlalchemy import func  # noqa: PLC0415

    stmt = select(func.count(UserGroupMembership.uid)).where(
        UserGroupMembership.user_group_uid == group.uid
    )
    return int(db.execute(stmt).scalar_one())


def _load_membership_for_access(
    db: DBSession, user: User, membership_uid: str
) -> tuple[UserGroupMembership, UserGroup]:
    """Load (membership, its group) if the caller is the member or the group's owner."""
    stmt = (
        select(UserGroupMembership, UserGroup)
        .join(UserGroup, UserGroup.uid == UserGroupMembership.user_group_uid)
        .where(UserGroupMembership.uid == membership_uid)
        .where(UserGroup.archived.is_(False))
    )
    row = db.execute(stmt).one_or_none()
    if row is None:
        raise UserGroupMembershipNotFoundError(membership_uid)

    membership, group = row
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


def invite_member(
    db: DBSession,
    *,
    group: UserGroup,
    user_to_add: User,
    invited_by: User,
) -> UserGroupMembership:
    """Internal helper: add an existing user to a group.

    Not exposed via HTTP in this PR — the public flow is invitation-based
    (next PR). Kept here as the single point at which membership rows are
    created so test fixtures and the future invitation-accept service share
    the same uniqueness handling.
    """
    membership = UserGroupMembership(
        user_uid=user_to_add.uid,
        user_group_uid=group.uid,
        invited_by_uid=invited_by.uid,
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
