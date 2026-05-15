"""Tests for the user-group-memberships router."""

from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.app.repository import (
    User,
    UserGroup,
    UserGroupMembership,
)


def _membership_uid(db: Session, group: UserGroup, user: User) -> str:
    stmt = (
        select(UserGroupMembership.uid)
        .where(UserGroupMembership.user_group_uid == group.uid)
        .where(UserGroupMembership.user_uid == user.uid)
    )
    return db.execute(stmt).scalar_one()


def test_self_leaves_group(
    client: TestClient,
    test_db: Session,
    test_user: User,
    create_user: Callable[..., User],
    create_group: Callable[..., UserGroup],
    create_membership: Callable[..., None],
):
    owner = create_user()
    group = create_group(name="Theirs", owner=owner)
    create_membership(group=group, user=test_user)
    membership_uid = _membership_uid(test_db, group, test_user)

    response = client.delete(f"/api/v1/user-group-memberships/{membership_uid}")
    assert response.status_code == 204

    # The caller can no longer see the group (no membership left).
    response = client.get(f"/api/v1/user-groups/{group.uid}")
    assert response.status_code == 404


def test_sole_owner_cannot_leave_group_with_other_members(
    client: TestClient,
    test_db: Session,
    test_user: User,
    create_user: Callable[..., User],
    create_group: Callable[..., UserGroup],
    create_membership: Callable[..., None],
):
    other = create_user()
    group = create_group(name="Mine", owner=test_user)
    create_membership(group=group, user=other)
    membership_uid = _membership_uid(test_db, group, test_user)

    response = client.delete(f"/api/v1/user-group-memberships/{membership_uid}")
    assert response.status_code == 409


def test_sole_owner_can_leave_empty_group(
    client: TestClient,
    test_db: Session,
    test_user: User,
    create_group: Callable[..., UserGroup],
):
    group = create_group(name="Solo", owner=test_user)
    membership_uid = _membership_uid(test_db, group, test_user)

    response = client.delete(f"/api/v1/user-group-memberships/{membership_uid}")
    assert response.status_code == 204


def test_owner_can_remove_other_member(
    client: TestClient,
    test_db: Session,
    test_user: User,
    create_user: Callable[..., User],
    create_group: Callable[..., UserGroup],
    create_membership: Callable[..., None],
):
    other = create_user()
    group = create_group(name="Mine", owner=test_user)
    create_membership(group=group, user=other)
    membership_uid = _membership_uid(test_db, group, other)

    response = client.delete(f"/api/v1/user-group-memberships/{membership_uid}")
    assert response.status_code == 204


def test_non_owner_cannot_remove_other_member(
    client: TestClient,
    test_db: Session,
    test_user: User,
    create_user: Callable[..., User],
    create_group: Callable[..., UserGroup],
    create_membership: Callable[..., None],
    authenticate_as: Callable[[User], TestClient],
):
    owner = create_user(email="owner@example.com")
    third = create_user(email="third@example.com")
    group = create_group(name="Theirs", owner=owner)
    create_membership(group=group, user=test_user)
    create_membership(group=group, user=third)
    third_membership_uid = _membership_uid(test_db, group, third)

    response = client.delete(f"/api/v1/user-group-memberships/{third_membership_uid}")
    # test_user is neither the target nor the owner → 404 (don't leak existence).
    assert response.status_code == 404


def test_unauthenticated_membership_endpoints(
    unauthenticated_client: TestClient,
):
    response = unauthenticated_client.delete("/api/v1/user-group-memberships/anything")
    assert response.status_code == 401
