"""Tests for permission predicates and the capability product."""

from collections.abc import Callable

import pytest
from sqlalchemy.orm import Session

from src.app.repository import (
    Equals,
    HexClaim,
    HexClaimByCell,
    Related,
    Repository,
    ResourceType,
    Upload,
    User,
    UserGroup,
    UserGroupMembership,
    UserSession,
)
from src.app.repository.predicates import Guard
from src.app.services.permissions import (
    Capability,
    Operation,
    capabilities_for,
    permissions_predicates,
    predicates_hold,
)
from src.app.services.workspace import WORKSPACE


def test_upload_permission_predicates(test_user: User):
    predicates = permissions_predicates(test_user, Upload)
    assert predicates is not None
    assert len(predicates) == 1
    p = predicates[0]
    assert isinstance(p, Equals)
    assert p.field == "user_uid"
    assert p.value == test_user.uid  # pyright: ignore[reportUnknownMemberType]


def test_hex_claim_permission_predicates(test_user: User):
    predicates = permissions_predicates(test_user, HexClaim)
    assert predicates is not None
    assert len(predicates) == 1
    p = predicates[0]
    assert isinstance(p, Equals)
    assert p.field == "user_uid"
    assert p.value == test_user.uid  # pyright: ignore[reportUnknownMemberType]


def test_hex_claim_by_cell_permission_predicates(test_user: User):
    predicates = permissions_predicates(test_user, HexClaimByCell)
    assert predicates is not None
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

    predicates = permissions_predicates(test_user, UserGroup, Operation.READ)
    assert predicates is not None
    result = Repository(test_db, UserGroup).get_filtered(filters=predicates)

    assert {g.name for g in result.items} == {"Owned", "MemberOf"}


def test_user_group_update_predicate_is_owner_only(test_user: User):
    """UPDATE narrows to a single owner Equals — no membership leg."""
    predicates = permissions_predicates(test_user, UserGroup, Operation.UPDATE)
    assert predicates is not None
    assert len(predicates) == 1
    p = predicates[0]
    assert isinstance(p, Equals)
    assert p.field == "owner_uid"
    assert p.value == test_user.uid  # pyright: ignore[reportUnknownMemberType]


def test_undefined_operation_returns_none(test_user: User):
    """An operation an entity doesn't define yields None (nobody holds it) —
    distinct from `[]` (unconditionally allowed)."""
    assert permissions_predicates(test_user, UserGroup, Operation.DELETE) is None
    assert permissions_predicates(test_user, Upload, Operation.DELETE) is None


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


# --- capabilities_for: object-level --------------------------------------


def test_capabilities_for_group_owner(
    test_db: Session,
    test_user: User,
    create_group: Callable[..., UserGroup],
):
    """An owner holds READ + UPDATE on their group — no DELETE (undefined)."""
    group = create_group(name="Owned", owner=test_user)
    caps = capabilities_for(test_db, test_user, group)
    assert caps == {
        Capability(Operation.READ, ResourceType.USER_GROUP),
        Capability(Operation.UPDATE, ResourceType.USER_GROUP),
    }


def test_capabilities_for_group_member_not_owner(
    test_db: Session,
    test_user: User,
    create_user: Callable[..., User],
    create_group: Callable[..., UserGroup],
    create_membership: Callable[..., UserGroupMembership],
):
    """A member who is not the owner holds READ only — no UPDATE."""
    owner = create_user(email="owner@example.com")
    group = create_group(name="MemberOf", owner=owner)
    create_membership(group=group, user=test_user)
    caps = capabilities_for(test_db, test_user, group)
    assert caps == {Capability(Operation.READ, ResourceType.USER_GROUP)}


def test_capabilities_for_upload_owner(
    test_db: Session,
    test_user: User,
    create_upload: Callable[..., Upload],
):
    """An upload's owner holds READ + UPDATE on it."""
    upload = create_upload("ride.gpx")
    caps = capabilities_for(test_db, test_user, upload)
    assert caps == {
        Capability(Operation.READ, ResourceType.UPLOAD),
        Capability(Operation.UPDATE, ResourceType.UPLOAD),
    }


# --- capabilities_for: collection-level (the WORKSPACE handle) -----------


def test_capabilities_for_workspace_non_admin(test_db: Session, test_user: User):
    """A non-admin may create groups and uploads, but not users."""
    caps = capabilities_for(test_db, test_user, WORKSPACE)
    assert Capability(Operation.CREATE, ResourceType.USER_GROUP) in caps
    assert Capability(Operation.CREATE, ResourceType.UPLOAD) in caps
    assert Capability(Operation.CREATE, ResourceType.USER) not in caps


def test_capabilities_for_workspace_admin(
    test_db: Session,
    create_user: Callable[..., User],
):
    """An admin may additionally create users."""
    admin = create_user(email="admin@example.com")
    admin.is_admin = True
    test_db.commit()
    caps = capabilities_for(test_db, admin, WORKSPACE)
    assert caps == {
        Capability(Operation.CREATE, ResourceType.USER_GROUP),
        Capability(Operation.CREATE, ResourceType.UPLOAD),
        Capability(Operation.CREATE, ResourceType.USER),
    }


# --- predicates_hold: the relational re-query branch ------------------------------


def test_holds_relational_requery(
    test_db: Session,
    test_user: User,
    create_user: Callable[..., User],
    create_group: Callable[..., UserGroup],
    create_membership: Callable[..., UserGroupMembership],
):
    """`predicates_hold` falls back to a re-query for relational (non-Guard) predicates.

    The UserGroup READ predicate is an `Or(owner, Related(members))` — not a
    `Guard` — so `predicates_hold` cannot answer it in memory and must hit the DB. A
    member satisfies it; a stranger does not.
    """
    owner = create_user(email="owner@example.com")
    group = create_group(name="MemberOf", owner=owner)
    create_membership(group=group, user=test_user)
    stranger = create_user(email="stranger@example.com")

    member_predicates = permissions_predicates(test_user, UserGroup, Operation.READ)
    stranger_predicates = permissions_predicates(stranger, UserGroup, Operation.READ)
    assert member_predicates is not None
    assert stranger_predicates is not None

    assert predicates_hold(test_db, group, member_predicates) is True
    assert predicates_hold(test_db, group, stranger_predicates) is False
