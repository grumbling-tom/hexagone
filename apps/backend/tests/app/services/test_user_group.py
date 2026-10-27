"""Service-level tests for user groups."""

from collections.abc import Callable

import pytest
from sqlalchemy.orm import Session

from src.app.repository import (
    NotAuthorisedError,
    ScopedRepository,
    SystemPolicy,
    UnitOfWork,
    User,
    UserGroup,
    UserGroupMembership,
)
from src.app.services import user_group as user_group_service
from src.app.services.permissions import ViewerPolicy


@pytest.fixture
def groups(test_db: Session, test_user: User) -> ScopedRepository[UserGroup]:
    """UserGroup repository scoped to ``test_user``."""
    return ScopedRepository(test_db, UserGroup, ViewerPolicy(test_user))


@pytest.fixture
def memberships(
    test_db: Session, test_user: User
) -> ScopedRepository[UserGroupMembership]:
    """UserGroupMembership repository scoped to ``test_user``."""
    return ScopedRepository(test_db, UserGroupMembership, ViewerPolicy(test_user))


def test_create_group_creates_owner_membership(
    test_db: Session,
    test_user: User,
    groups: ScopedRepository[UserGroup],
    memberships: ScopedRepository[UserGroupMembership],
    uow: UnitOfWork,
):
    group = user_group_service.create_group(
        groups, memberships, uow, test_user, name="Solo"
    )

    assert group.owner_uid == test_user.uid
    assert group.archived is False

    members = user_group_service.list_members(groups, memberships, group.uid).items
    assert len(members) == 1
    assert members[0].user_uid == test_user.uid


def test_create_guard_rejects_group_owned_by_someone_else(
    test_db: Session,
    test_user: User,
    create_user: Callable[..., User],
    groups: ScopedRepository[UserGroup],
):
    """The viewer's CREATE guards reject an instance whose owner isn't the
    viewer, before anything is inserted — no caller has to remember them."""
    other = create_user(email="other@example.com")

    with pytest.raises(NotAuthorisedError):
        groups.create(UserGroup(name="Forged", owner_uid=other.uid))

    assert ScopedRepository(test_db, UserGroup, SystemPolicy()).get_all().items == []


def test_add_member_as_owner_adds_membership(
    test_db: Session,
    test_user: User,
    create_user: Callable[..., User],
    create_group: Callable[..., UserGroup],
    groups: ScopedRepository[UserGroup],
    memberships: ScopedRepository[UserGroupMembership],
    uow: UnitOfWork,
):
    other = create_user(email="other@example.com")
    group = create_group(name="Mine", owner=test_user)

    membership = user_group_service.add_member(
        groups, memberships, uow, group.uid, other.uid
    )

    assert membership.user_uid == other.uid
    assert membership.user_group_uid == group.uid
    member_uids = {
        m.user_uid
        for m in user_group_service.list_members(groups, memberships, group.uid).items
    }
    assert member_uids == {test_user.uid, other.uid}


def test_add_member_as_non_owner_raises_not_found(
    test_db: Session,
    test_user: User,
    create_user: Callable[..., User],
    create_group: Callable[..., UserGroup],
    groups: ScopedRepository[UserGroup],
    memberships: ScopedRepository[UserGroupMembership],
    uow: UnitOfWork,
):
    """A caller who doesn't own the group can't add members — the relational
    UPDATE read returns nothing, so it's a 404-shaped `UserGroupNotFoundError`."""
    owner = create_user(email="owner@example.com")
    outsider = create_user(email="outsider@example.com")
    group = create_group(name="Theirs", owner=owner)

    with pytest.raises(user_group_service.UserGroupNotFoundError):
        user_group_service.add_member(groups, memberships, uow, group.uid, outsider.uid)


def test_add_member_rejects_duplicates(
    test_db: Session,
    test_user: User,
    create_user: Callable[..., User],
    create_group: Callable[..., UserGroup],
    groups: ScopedRepository[UserGroup],
    memberships: ScopedRepository[UserGroupMembership],
    uow: UnitOfWork,
):
    other = create_user(email="other@example.com")
    group = create_group(name="Mine", owner=test_user)

    user_group_service.add_member(groups, memberships, uow, group.uid, other.uid)

    with pytest.raises(user_group_service.DuplicateMembershipError):
        user_group_service.add_member(groups, memberships, uow, group.uid, other.uid)


def test_archive_group_as_owner_soft_deletes(
    test_db: Session,
    test_user: User,
    create_group: Callable[..., UserGroup],
    groups: ScopedRepository[UserGroup],
    uow: UnitOfWork,
):
    group = create_group(name="Doomed", owner=test_user)

    archived = user_group_service.archive_group(groups, uow, group.uid)

    assert archived.uid == group.uid
    assert archived.archived is True
    remaining = user_group_service.list_groups(groups).items
    assert group.uid not in {g.uid for g in remaining}


def test_archive_group_is_idempotent(
    test_db: Session,
    test_user: User,
    create_group: Callable[..., UserGroup],
    groups: ScopedRepository[UserGroup],
    uow: UnitOfWork,
):
    """Re-archiving an already-archived group hits the `archived == False`
    guard and matches no row, so `repo.update` raises `NotAuthorisedError`."""
    group = create_group(name="Doomed", owner=test_user)
    user_group_service.archive_group(groups, uow, group.uid)

    with pytest.raises(NotAuthorisedError):
        user_group_service.archive_group(groups, uow, group.uid)


def test_list_groups_excludes_archived(
    test_db: Session,
    test_user: User,
    create_group: Callable[..., UserGroup],
    groups: ScopedRepository[UserGroup],
    uow: UnitOfWork,
):
    live = create_group(name="Live")
    create_group(name="Doomed")

    doomed_uid = next(
        g.uid
        for g in user_group_service.list_groups(groups).items
        if g.name == "Doomed"
    )
    user_group_service.archive_group(groups, uow, doomed_uid)

    remaining = user_group_service.list_groups(groups).items
    assert [g.uid for g in remaining] == [live.uid]


def test_archive_group_for_non_owner_raises_not_authorised(
    test_db: Session,
    test_user: User,
    create_user: Callable[..., User],
    create_group: Callable[..., UserGroup],
    create_membership: Callable[..., UserGroupMembership],
    groups: ScopedRepository[UserGroup],
    uow: UnitOfWork,
):
    """A non-owner (even a member) matches no row under the UPDATE guard, so
    `archive_group` raises `NotAuthorisedError` — surfaced app-wide as 403."""
    owner = create_user(email="owner@example.com")
    group = create_group(name="Theirs", owner=owner)
    create_membership(group=group, user=test_user)

    with pytest.raises(NotAuthorisedError):
        user_group_service.archive_group(groups, uow, group.uid)


def test_get_group_for_non_member_returns_none(
    test_db: Session,
    test_user: User,
    create_user: Callable[..., User],
    create_group: Callable[..., UserGroup],
    groups: ScopedRepository[UserGroup],
):
    """`get_group` returns `None` for "not found / not visible" — routers
    translate that to 404. See CLAUDE.md "Return None for Absence"."""
    other = create_user(email="other@example.com")
    group = create_group(name="Theirs", owner=other)

    assert user_group_service.get_group(groups, group.uid) is None


def test_remove_membership_is_not_implemented(
    test_db: Session,
    test_user: User,
    memberships: ScopedRepository[UserGroupMembership],
):
    """Membership management is deferred — `remove_membership` is a stub
    until the membership feature is designed properly."""
    with pytest.raises(NotImplementedError):
        user_group_service.remove_membership(memberships, "any-uid")
