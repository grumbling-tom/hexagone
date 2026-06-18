"""Service layer for user groups and their memberships."""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DBSession

from src.app.repository import (
    Equals,
    Repository,
    User,
    UserGroup,
    UserGroupMembership,
)
from src.app.repository.predicates import Filter
from src.app.services.permissions import Operation, permissions_predicates
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
    operation: Operation = Operation.READ,
) -> UserGroup | None:
    """Return a group the caller can access for `operation`; else None.

    `operation=WRITE` narrows visibility to groups the caller owns — useful as a
    relational authorization gate (e.g. "actor owns the group" before inserting
    a membership row).
    """
    try:
        return list_groups(
            db,
            user,
            group_uid=group_uid,
            operation=operation,
        ).items[0]
    except IndexError:
        return None


def list_groups(  # noqa: PLR0913
    db: DBSession,
    user: User,
    page_size: int = settings.DEFAULT_PAGE_SIZE,
    cursor: str | None = None,
    group_uid: str | None = None,
    operation: Operation = Operation.READ,
    sort_field: str = "created_at",
    sort_order: SortOrder = SortOrder.DESC,
) -> PaginatedResult[UserGroup]:
    """Return non-archived groups the caller can access for `operation`."""
    repo = Repository(db, UserGroup)

    filters: list[Filter] = [
        *permissions_predicates(user, UserGroup, operation),
        Equals(field="archived", value=False),
    ]

    if group_uid is not None:
        filters.append(Equals(field="uid", value=group_uid))

    return repo.get_filtered(
        filters=filters,
        sort_field=getattr(UserGroup, sort_field),
        sort_order=sort_order,
        page_size=page_size,
        cursor=cursor,
    )


def update_group(db: DBSession, user: User, group_uid: str, *, name: str) -> UserGroup:
    """Rename a group. Owner-only.

    The owner check rides as a SQL guard on the UPDATE itself, so authorization
    and mutation are one atomic statement (no read-then-write race).
    """
    repo = Repository(db, UserGroup)
    group = repo.update(
        group_uid,
        {"name": name},
        guards=permissions_predicates(user, UserGroup, Operation.WRITE),
    )

    db.commit()
    return group


def archive_group(db: DBSession, user: User, group_uid: str) -> UserGroup:
    """Soft-delete a group. Owner-only, atomic, and idempotent.

    The guards reproduce every WHERE the old gating read applied: the WRITE
    permission predicates plus `archived == False`. A non-owner, a missing
    group, or an already-archived group all match no row, so `repo.update`
    raises `NotAuthorisedError` (handled app-wide as a 403).
    """
    repo = Repository(db, UserGroup)
    group = repo.update(
        group_uid,
        {"archived": True},
        guards=[
            *permissions_predicates(user, UserGroup, Operation.WRITE),
            Equals(field="archived", value=False),
        ],
    )
    db.commit()
    logger.info("user_group_archived", user_group_uid=group.uid)
    return group


def list_members(
    db: DBSession,
    user: User,
    group_uid: str,
    *,
    page_size: int = settings.DEFAULT_PAGE_SIZE,
    cursor: str | None = None,
) -> PaginatedResult[UserGroupMembership]:
    """Return memberships of a group the caller belongs to."""
    group = get_group(db, user, group_uid)

    if group is None:
        raise UserGroupNotFoundError(group_uid)

    repo = Repository(db, UserGroupMembership)
    return repo.get_filtered(
        filters=[Equals(field="user_group_uid", value=group.uid)],
        sort_field=UserGroupMembership.created_at,
        sort_order=SortOrder.ASC,
        page_size=page_size,
        cursor=cursor,
    )


def remove_membership(db: DBSession, user: User, membership_uid: str) -> None:
    """Delete a membership."""
    raise NotImplementedError


def add_member(
    db: DBSession,
    actor: User,
    group_uid: str,
    member_uid: str,
) -> UserGroupMembership:
    """Add `member_uid` to a group. Owner-only.

    Authorization is of two kinds, exercising the two enforcement mechanisms:

      * RELATIONAL ("actor owns the group") — a fact about the PARENT group, not
        the membership row. It can't be a create `Guard`: on the read side it is
        a `Related`/EXISTS predicate, which is a `Filter`, and a `Filter` is not
        a `Guard`. So it's enforced by a permissioned READ of the group.

      * SAME-ROW INVARIANT ("the new membership is scoped to the authorized
        group") — expressible as a `Guard`, so it rides as a `create` guard.
        Defense-in-depth for this server-built row; substantive when the row
        comes from untrusted input.
    """
    group = get_group(db, actor, group_uid, operation=Operation.WRITE)
    if group is None:
        raise UserGroupNotFoundError(group_uid)

    memberships = Repository(db, UserGroupMembership)
    try:
        membership = memberships.create(
            UserGroupMembership(user_uid=member_uid, user_group_uid=group.uid),
            guards=[Equals(field="user_group_uid", value=group.uid)],
        )
        db.commit()  # create() already flushed; IntegrityError surfaces there
    except IntegrityError:
        db.rollback()
        msg = f"User {member_uid} already a member of {group.uid}"
        raise DuplicateMembershipError(msg) from None

    db.refresh(membership)
    logger.info(
        "user_group_member_added",
        user_group_uid=group.uid,
        user_uid=member_uid,
    )
    return membership
