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

    members = user_group_service.list_members(test_db, test_user, group.uid)
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


def test_list_groups_for_user_excludes_archived(
    test_db: Session,
    test_user: User,
    create_group: Callable[..., UserGroup],
):
    live = create_group(name="Live")
    create_group(name="Doomed")

    user_group_service.archive_group(
        test_db,
        test_user,
        next(
            g.uid
            for g in user_group_service.list_groups_for_user(test_db, test_user)
            if g.name == "Doomed"
        ),
    )

    remaining = user_group_service.list_groups_for_user(test_db, test_user)
    assert [g.uid for g in remaining] == [live.uid]


def test_archive_group_requires_owner(
    test_db: Session,
    test_user: User,
    create_user: Callable[..., User],
    create_group: Callable[..., UserGroup],
    create_membership: Callable[..., UserGroupMembership],
):
    owner = create_user()
    group = create_group(name="Theirs", owner=owner)
    create_membership(group=group, user=test_user)

    with pytest.raises(user_group_service.NotGroupOwnerError):
        user_group_service.archive_group(test_db, test_user, group.uid)


def test_get_group_for_non_member_raises(
    test_db: Session,
    test_user: User,
    create_user: Callable[..., User],
    create_group: Callable[..., UserGroup],
):
    other = create_user()
    group = create_group(name="Theirs", owner=other)

    with pytest.raises(user_group_service.UserGroupNotFoundError):
        user_group_service.get_group(test_db, test_user, group.uid)


def test_remove_owner_with_other_members_rejected(
    test_db: Session,
    test_user: User,
    create_user: Callable[..., User],
    create_group: Callable[..., UserGroup],
    create_membership: Callable[..., UserGroupMembership],
):
    other = create_user()
    group = create_group(name="Mine", owner=test_user)
    create_membership(group=group, user=other)

    [owner_membership] = [
        m
        for m in user_group_service.list_members(test_db, test_user, group.uid)
        if m.user_uid == test_user.uid
    ]

    with pytest.raises(user_group_service.SoleOwnerCannotLeaveError):
        user_group_service.remove_membership(test_db, test_user, owner_membership.uid)
