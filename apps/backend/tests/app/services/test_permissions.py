"""Tests for the viewer row rules (``row_rules``)."""

from collections.abc import Callable

import pytest
from sqlalchemy.orm import Session

from src.app.repository import (
    Equals,
    HexClaim,
    HexClaimByCell,
    Related,
    ScopedRepository,
    Upload,
    User,
    UserGroup,
    UserGroupMembership,
    UserSession,
)
from src.app.repository.predicates import Guard
from src.app.services.permissions import Operation, ViewerPolicy, row_rules


def test_upload_permission_predicates(test_user: User):
    predicates = row_rules(test_user, Upload)
    assert len(predicates) == 1
    p = predicates[0]
    assert isinstance(p, Equals)
    assert p.field == "user_uid"
    assert p.value == test_user.uid  # pyright: ignore[reportUnknownMemberType]


def test_hex_claim_permission_predicates(test_user: User):
    predicates = row_rules(test_user, HexClaim)
    assert len(predicates) == 1
    p = predicates[0]
    assert isinstance(p, Equals)
    assert p.field == "user_uid"
    assert p.value == test_user.uid  # pyright: ignore[reportUnknownMemberType]


def test_hex_claim_by_cell_permission_predicates(test_user: User):
    predicates = row_rules(test_user, HexClaimByCell)
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

    result = ScopedRepository(test_db, UserGroup, ViewerPolicy(test_user)).get_all()

    assert {g.name for g in result.items} == {"Owned", "MemberOf"}


def test_user_group_update_predicate_is_owner_only(test_user: User):
    """UPDATE narrows to a single owner Equals — no membership leg."""
    predicates = row_rules(test_user, UserGroup, Operation.UPDATE)
    assert len(predicates) == 1
    p = predicates[0]
    assert isinstance(p, Equals)
    assert p.field == "owner_uid"
    assert p.value == test_user.uid  # pyright: ignore[reportUnknownMemberType]


def test_user_group_create_guard_admits_only_own_groups(
    test_user: User, create_user: Callable[..., User]
):
    """CREATE yields `Guard`s judged against the in-memory instance: a user may
    create a group they own, but not one owned by somebody else."""
    other = create_user(email="other@example.com")
    guards = row_rules(test_user, UserGroup, Operation.CREATE)

    own = UserGroup(name="Mine", owner_uid=test_user.uid)
    theirs = UserGroup(name="Theirs", owner_uid=other.uid)

    assert all(isinstance(g, Guard) for g in guards)
    assert all(g.is_satisfied_by(own) for g in guards)
    assert not all(g.is_satisfied_by(theirs) for g in guards)


def test_upload_create_guard_admits_only_own_uploads(test_user: User):
    guards = row_rules(test_user, Upload, Operation.CREATE)

    own = Upload(user_uid=test_user.uid)
    theirs = Upload(user_uid="someone-else")

    assert all(g.is_satisfied_by(own) for g in guards)
    assert not all(g.is_satisfied_by(theirs) for g in guards)


@pytest.mark.parametrize("operation", [Operation.CREATE, Operation.UPDATE])
def test_read_only_view_rejects_writes(test_user: User, operation: Operation):
    with pytest.raises(ValueError, match=f"No {operation} permission predicates"):
        row_rules(test_user, HexClaimByCell, operation)  # pyright: ignore[reportCallIssue,reportArgumentType]


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
        ValueError, match="No read permission predicates defined for UserSession"
    ):
        row_rules(test_user, UserSession)
