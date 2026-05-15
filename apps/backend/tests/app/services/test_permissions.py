"""Tests for permission filters."""

from collections.abc import Callable

import pytest
from sqlalchemy.orm import Session

from src.app.repository import (
    EqualsFilter,
    HexClaim,
    HexClaimByCell,
    Repository,
    Upload,
    User,
    UserGroup,
    UserGroupMembership,
    UserSession,
)
from src.app.services.permissions import permission_filters


def test_upload_permission_filters(test_user: User):
    filters = permission_filters(test_user, Upload)
    assert len(filters) == 1
    f = filters[0]
    assert isinstance(f, EqualsFilter)
    assert f.field == "user_uid"
    assert f.value == test_user.uid  # pyright: ignore[reportUnknownMemberType]


def test_hex_claim_permission_filters(test_user: User):
    filters = permission_filters(test_user, HexClaim)
    assert len(filters) == 1
    f = filters[0]
    assert isinstance(f, EqualsFilter)
    assert f.field == "user_uid"
    assert f.value == test_user.uid  # pyright: ignore[reportUnknownMemberType]


def test_hex_claim_by_cell_permission_filters(test_user: User):
    filters = permission_filters(test_user, HexClaimByCell)
    assert len(filters) == 1
    f = filters[0]
    assert isinstance(f, EqualsFilter)
    assert f.field == "user_uid"
    assert f.value == test_user.uid  # pyright: ignore[reportUnknownMemberType]


def test_user_group_permission_filter_returns_owned_and_member_groups(
    test_db: Session,
    test_user: User,
    create_user: Callable[..., User],
    create_group: Callable[..., UserGroup],
    create_membership: Callable[..., UserGroupMembership],
):
    """A user should be able to see groups they own and groups they're a
    member of, but no others. Exercises the composition of OrFilter +
    EqualsFilter (for ownership) + RelationFilter (for membership)."""
    other = create_user(email="other@example.com")

    # test_user owns this one (and is auto-enrolled as a member).
    create_group(name="Owned", owner=test_user)
    # test_user is a member of this one but doesn't own it.
    member_of = create_group(name="MemberOf", owner=other)
    create_membership(group=member_of, user=test_user, invited_by=other)
    # test_user has nothing to do with this one.
    create_group(name="Stranger", owner=other)

    result = Repository(test_db, UserGroup).get_filtered(
        filters=permission_filters(test_user, UserGroup),
    )

    assert {g.name for g in result.items} == {"Owned", "MemberOf"}


def test_unknown_entity_raises(test_user: User):
    with pytest.raises(
        ValueError, match="No permission filters defined for UserSession"
    ):
        permission_filters(test_user, UserSession)
