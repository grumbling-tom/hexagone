"""Service-level tests for user groups."""

from collections.abc import Callable

import pytest
from sqlalchemy.orm import Session

from src.app.repository import User, UserGroup, UserGroupMembership
from src.app.services import user_group as user_group_service


def test_create_group_creates_owner_membership(test_db: Session, test_user: User):
    group = user_group_service.create_group(test_db, test_user, name="Solo")

    assert group.owner_uid == test_user.uid
    assert group.archived is False

    members = user_group_service.list_members(test_db, test_user, group.uid).items
    assert len(members) == 1
    assert members[0].user_uid == test_user.uid


def test_add_member_rejects_duplicates(
    test_db: Session,
    test_user: User,
    create_user: Callable[..., User],
    create_group: Callable[..., UserGroup],
):
    other = create_user()
    group = create_group(name="Mine", owner=test_user)

    user_group_service.add_member(test_db, group=group, user_to_add=other)

    with pytest.raises(user_group_service.DuplicateMembershipError):
        user_group_service.add_member(test_db, group=group, user_to_add=other)


def test_list_groups_excludes_archived(
    test_db: Session,
    test_user: User,
    create_group: Callable[..., UserGroup],
):
    live = create_group(name="Live")
    create_group(name="Doomed")

    doomed_uid = next(
        g.uid
        for g in user_group_service.list_groups(test_db, test_user).items
        if g.name == "Doomed"
    )
    user_group_service.archive_group(test_db, test_user, doomed_uid)

    remaining = user_group_service.list_groups(test_db, test_user).items
    assert [g.uid for g in remaining] == [live.uid]


def test_archive_group_for_non_owner_raises_not_found(
    test_db: Session,
    test_user: User,
    create_user: Callable[..., User],
    create_group: Callable[..., UserGroup],
    create_membership: Callable[..., UserGroupMembership],
):
    """Non-owners get the same 404-shaped result as non-members — the
    `owner_only` filter on `get_group` means the row simply isn't visible
    to them in the context of a mutation, so `update_group` /
    `archive_group` raise `UserGroupNotFoundError` rather than a
    permission-specific error."""
    owner = create_user()
    group = create_group(name="Theirs", owner=owner)
    create_membership(group=group, user=test_user)

    with pytest.raises(user_group_service.UserGroupNotFoundError):
        user_group_service.archive_group(test_db, test_user, group.uid)


def test_get_group_for_non_member_returns_none(
    test_db: Session,
    test_user: User,
    create_user: Callable[..., User],
    create_group: Callable[..., UserGroup],
):
    """`get_group` returns `None` for "not found / not visible" — routers
    translate that to 404. See CLAUDE.md "Return None for Absence"."""
    other = create_user()
    group = create_group(name="Theirs", owner=other)

    assert user_group_service.get_group(test_db, test_user, group.uid) is None


def test_remove_membership_is_not_implemented(test_db: Session, test_user: User):
    """Membership management is deferred — `remove_membership` is a stub
    until the membership feature is designed properly."""
    with pytest.raises(NotImplementedError):
        user_group_service.remove_membership(test_db, test_user, "any-uid")
