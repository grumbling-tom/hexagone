"""Service layer for user groups and their memberships."""

from typing import Literal

from sqlalchemy.exc import IntegrityError

from src.app.repository import (
    Equals,
    Operation,
    Predicate,
    ScopedRepository,
    Transaction,
    User,
    UserGroup,
    UserGroupMembership,
)
from src.app.settings import settings
from src.app.utils import PaginatedResult, SortOrder, get_logger

logger = get_logger(__name__)


class UserGroupNotFoundError(Exception):
    """Group not found, archived, or not visible to the requesting user."""


class DuplicateMembershipError(Exception):
    """A membership row already exists for this (user, group) pair."""


def create_group(
    groups: ScopedRepository[UserGroup],
    memberships: ScopedRepository[UserGroupMembership],
    tx: Transaction,
    owner: User,
    name: str,
) -> UserGroup:
    """Create a new group with `owner` as the sole initial member.

    The caller is recorded as the group's owner and automatically gets a
    membership row. The policy's CREATE guards check the in-memory instance
    before the INSERT: a group whose `owner_uid` isn't the viewer is rejected
    with `NotAuthorisedError`.
    """
    group = groups.create(UserGroup(name=name, owner_uid=owner.uid, archived=False))
    memberships.create(
        UserGroupMembership(user_uid=owner.uid, user_group_uid=group.uid)
    )
    tx.commit()

    logger.info(
        "user_group_created",
        user_group_uid=group.uid,
        owner_uid=owner.uid,
    )
    return group


def get_group(
    groups: ScopedRepository[UserGroup],
    group_uid: str,
    operation: Literal[Operation.READ, Operation.UPDATE] = Operation.READ,
) -> UserGroup | None:
    """Return a group the caller can access for `operation`; else None.

    `operation=UPDATE` narrows visibility to groups the caller owns — useful as a
    relational authorization gate (e.g. "actor owns the group" before inserting
    a membership row).
    """
    try:
        return list_groups(
            groups,
            group_uid=group_uid,
            operation=operation,
        ).items[0]
    except IndexError:
        return None


def list_groups(  # noqa: PLR0913
    groups: ScopedRepository[UserGroup],
    page_size: int = settings.DEFAULT_PAGE_SIZE,
    cursor: str | None = None,
    group_uid: str | None = None,
    operation: Literal[Operation.READ, Operation.UPDATE] = Operation.READ,
    sort_field: str = "created_at",
    sort_order: SortOrder = SortOrder.DESC,
) -> PaginatedResult[UserGroup]:
    """Return non-archived groups the caller can access for `operation`.

    Every result is readable (the repository applies the READ rules). For
    `operation=UPDATE` the policy's UPDATE row rules are added as filters, so
    the rule "who may change a group" still lives in the policy.
    """
    filters: list[Predicate] = [Equals(field="archived", value=False)]
    if operation is Operation.UPDATE:
        filters.extend(groups.policy.rows(UserGroup, Operation.UPDATE))

    if group_uid is not None:
        filters.append(Equals(field="uid", value=group_uid))

    return groups.get_filtered(
        filters=filters,
        sort_field=getattr(UserGroup, sort_field),
        sort_order=sort_order,
        page_size=page_size,
        cursor=cursor,
    )


def update_group(
    groups: ScopedRepository[UserGroup], tx: Transaction, group_uid: str, *, name: str
) -> UserGroup:
    """Rename a group. Owner-only.

    The owner check is the policy's UPDATE rule, riding as a SQL guard on the
    UPDATE itself, so authorization and mutation are one atomic statement.
    """
    group = groups.update(group_uid, {"name": name})
    tx.commit()
    return group


def archive_group(
    groups: ScopedRepository[UserGroup], tx: Transaction, group_uid: str
) -> UserGroup:
    """Soft-delete a group. Owner-only, atomic, and idempotent.

    The policy's UPDATE rules plus `archived == False` ride in the WHERE. A
    non-owner, a missing group, or an already-archived group all match no row,
    so `update` raises `NotAuthorisedError` (handled app-wide as a 403).
    """
    group = groups.update(
        group_uid,
        {"archived": True},
        where=[Equals(field="archived", value=False)],
    )
    tx.commit()
    logger.info("user_group_archived", user_group_uid=group.uid)
    return group


def list_members(
    groups: ScopedRepository[UserGroup],
    memberships: ScopedRepository[UserGroupMembership],
    group_uid: str,
    *,
    page_size: int = settings.DEFAULT_PAGE_SIZE,
    cursor: str | None = None,
) -> PaginatedResult[UserGroupMembership]:
    """Return memberships of a group the caller belongs to."""
    group = get_group(groups, group_uid)

    if group is None:
        raise UserGroupNotFoundError(group_uid)

    return memberships.get_filtered(
        filters=[Equals(field="user_group_uid", value=group.uid)],
        sort_field=UserGroupMembership.created_at,
        sort_order=SortOrder.ASC,
        page_size=page_size,
        cursor=cursor,
    )


def remove_membership(
    memberships: ScopedRepository[UserGroupMembership], membership_uid: str
) -> None:
    """Delete a membership."""
    raise NotImplementedError


def add_member(
    groups: ScopedRepository[UserGroup],
    memberships: ScopedRepository[UserGroupMembership],
    tx: Transaction,
    group_uid: str,
    member_uid: str,
) -> UserGroupMembership:
    """Add `member_uid` to a group. Owner-only.

    "The viewer owns the group" is a fact about the PARENT group, not the
    membership row, so it can't be a create `Guard` (a guard only sees the
    instance being inserted). It's enforced by an owner-scoped read of the
    group. That check lives HERE, not in the policy — the membership CREATE
    rule is `Anyone()` — so this is the one write the policy can't vouch for.
    """
    group = get_group(groups, group_uid, operation=Operation.UPDATE)
    if group is None:
        raise UserGroupNotFoundError(group_uid)

    try:
        membership = memberships.create(
            UserGroupMembership(user_uid=member_uid, user_group_uid=group.uid)
        )
        tx.commit()  # create() already flushed; IntegrityError surfaces there
    except IntegrityError:
        tx.rollback()
        msg = f"User {member_uid} already a member of {group.uid}"
        raise DuplicateMembershipError(msg) from None

    logger.info(
        "user_group_member_added",
        user_group_uid=group.uid,
        user_uid=member_uid,
    )
    return membership
