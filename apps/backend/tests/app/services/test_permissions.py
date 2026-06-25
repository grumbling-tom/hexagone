"""Tests for permission predicates."""

from collections.abc import Callable

import pytest
from sqlalchemy.orm import Session

from src.app.repository import (
    Equals,
    HexClaim,
    HexClaimByCell,
    Related,
    Repository,
    Upload,
    User,
    UserGroup,
    UserGroupMembership,
    UserSession,
)
from src.app.repository.predicates import Guard
from src.app.services.permissions import Operation, permissions_predicates


def test_upload_permission_predicates(test_user: User):
    predicates = permissions_predicates(test_user, Upload)
    assert len(predicates) == 1
    p = predicates[0]
    assert isinstance(p, Equals)
    assert p.field == "user_uid"
    assert p.value == test_user.uid  # pyright: ignore[reportUnknownMemberType]


def test_hex_claim_permission_predicates(test_user: User):
    predicates = permissions_predicates(test_user, HexClaim)
    assert len(predicates) == 1
    p = predicates[0]
    assert isinstance(p, Equals)
    assert p.field == "user_uid"
    assert p.value == test_user.uid  # pyright: ignore[reportUnknownMemberType]


def test_hex_claim_by_cell_permission_predicates(test_user: User):
    predicates = permissions_predicates(test_user, HexClaimByCell)
    assert len(predicates) == 1
    p = predicates[0]
    assert isinstance(p, Equals)
    assert p.field == "user_uid"
    assert p.value == test_user.uid  # pyright: ignore[reportUnknownMemberType]


def test_user_group_read_predicate_returns_owned_and_member_groups(
    test_db: Session,
    test_user: User,
    create_user: Callable[..., User],
    create_group: Callable[..., UserGroup],
    create_membership: Callable[..., UserGroupMembership],
):
    """A user should be able to read groups they own and groups they're a
    member of, but no others. Exercises the composition of Or +
    Equals (for ownership) + Related (for membership)."""
    other = create_user(email="other@example.com")

    # test_user owns this one (and is auto-enrolled as a member).
    create_group(name="Owned", owner=test_user)
    # test_user is a member of this one but doesn't own it.
    member_of = create_group(name="MemberOf", owner=other)
    create_membership(group=member_of, user=test_user)
    # test_user has nothing to do with this one.
    create_group(name="Stranger", owner=other)

    result = Repository(test_db, UserGroup).get_filtered(
        filters=permissions_predicates(test_user, UserGroup, Operation.READ),
    )

    assert {g.name for g in result.items} == {"Owned", "MemberOf"}


def test_user_group_write_predicate_is_owner_only(test_user: User):
    """WRITE narrows to a single owner Equals — no membership leg."""
    predicates = permissions_predicates(test_user, UserGroup, Operation.WRITE)
    assert len(predicates) == 1
    p = predicates[0]
    assert isinstance(p, Equals)
    assert p.field == "owner_uid"
    assert p.value == test_user.uid  # pyright: ignore[reportUnknownMemberType]


def test_dual_mode_predicate_is_a_guard():
    """`Equals` defines `is_satisfied_by`, so it is structurally a `Guard`."""
    assert isinstance(Equals(field="x", value=1), Guard)


def test_relational_predicate_is_not_a_guard():
    """`Related` omits `is_satisfied_by`, so it is NOT a `Guard` — this is what
    keeps it out of `create(guards=...)` at type-check time."""
    related = Related(field="members", inner=Equals(field="uid", value="x"))
    assert not isinstance(related, Guard)


def test_unknown_entity_raises(test_user: User):
    with pytest.raises(
        ValueError, match="No permission predicates defined for UserSession"
    ):
        permissions_predicates(test_user, UserSession)
