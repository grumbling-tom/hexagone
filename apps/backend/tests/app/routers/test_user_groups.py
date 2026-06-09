"""Tests for the user-groups router."""

from collections.abc import Callable

from fastapi.testclient import TestClient

from src.app.repository import User, UserGroup


def test_create_user_group_success(client: TestClient, test_user: User):
    response = client.post("/api/v1/user-groups", json={"name": "Wanderers"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Wanderers"
    assert data["owner_uid"] == test_user.uid
    assert data["member_count"] == 1


def test_create_user_group_unauthenticated(unauthenticated_client: TestClient):
    response = unauthenticated_client.post(
        "/api/v1/user-groups", json={"name": "Wanderers"}
    )
    assert response.status_code == 401


def test_create_user_group_rejects_empty_name(client: TestClient):
    response = client.post("/api/v1/user-groups", json={"name": ""})
    assert response.status_code == 422


def test_list_user_groups_includes_owned(
    client: TestClient, create_group: Callable[..., UserGroup]
):
    create_group(name="One")
    create_group(name="Two")

    response = client.get("/api/v1/user-groups")
    assert response.status_code == 200
    names = {g["name"] for g in response.json()["items"]}
    assert names == {"One", "Two"}


def test_list_user_groups_excludes_groups_caller_is_not_in(
    client: TestClient,
    create_user: Callable[..., User],
    create_group: Callable[..., UserGroup],
):
    other = create_user()
    create_group(name="Theirs", owner=other)

    response = client.get("/api/v1/user-groups")
    assert response.status_code == 200
    assert response.json()["items"] == []


def test_list_user_groups_excludes_archived(
    client: TestClient, create_group: Callable[..., UserGroup]
):
    group = create_group(name="Doomed")
    client.delete(f"/api/v1/user-groups/{group.uid}")

    response = client.get("/api/v1/user-groups")
    assert response.status_code == 200
    assert response.json()["items"] == []


def test_get_user_group_as_member(
    client: TestClient, create_group: Callable[..., UserGroup]
):
    group = create_group(name="Mine")
    response = client.get(f"/api/v1/user-groups/{group.uid}")
    assert response.status_code == 200
    assert response.json()["uid"] == group.uid


def test_get_user_group_as_non_member_returns_404(
    client: TestClient,
    create_user: Callable[..., User],
    create_group: Callable[..., UserGroup],
):
    other = create_user()
    group = create_group(name="Theirs", owner=other)

    response = client.get(f"/api/v1/user-groups/{group.uid}")
    assert response.status_code == 404


def test_update_user_group_as_owner(
    client: TestClient, create_group: Callable[..., UserGroup]
):
    group = create_group(name="Old")
    response = client.patch(f"/api/v1/user-groups/{group.uid}", json={"name": "New"})
    assert response.status_code == 200
    assert response.json()["name"] == "New"


def test_update_user_group_as_non_owner_returns_404(
    client: TestClient,
    create_user: Callable[..., User],
    create_group: Callable[..., UserGroup],
    create_membership: Callable[..., None],
    test_user: User,
    authenticate_as: Callable[[User], TestClient],
):
    """Non-owners get 404, not 403 — the `owner_only` filter doesn't
    distinguish "doesn't exist" from "you can't update this", which keeps
    ownership of unrelated groups hidden from the caller."""
    owner = create_user()
    group = create_group(name="Theirs", owner=owner)
    create_membership(group=group, user=test_user)

    response = client.patch(f"/api/v1/user-groups/{group.uid}", json={"name": "Stolen"})
    assert response.status_code == 404


def test_delete_user_group_as_owner_soft_deletes(
    client: TestClient, create_group: Callable[..., UserGroup]
):
    group = create_group(name="Doomed")
    response = client.delete(f"/api/v1/user-groups/{group.uid}")
    assert response.status_code == 204

    # Subsequent GET returns 404 (archived groups not visible).
    response = client.get(f"/api/v1/user-groups/{group.uid}")
    assert response.status_code == 404


def test_delete_user_group_as_non_owner_returns_404(
    client: TestClient,
    create_user: Callable[..., User],
    create_group: Callable[..., UserGroup],
    create_membership: Callable[..., None],
    test_user: User,
):
    """Same rationale as the update case — 404 not 403."""
    owner = create_user()
    group = create_group(name="Theirs", owner=owner)
    create_membership(group=group, user=test_user)

    response = client.delete(f"/api/v1/user-groups/{group.uid}")
    assert response.status_code == 404


def test_member_count_reflects_membership_changes(
    client: TestClient,
    create_user: Callable[..., User],
    create_group: Callable[..., UserGroup],
    create_membership: Callable[..., None],
):
    other = create_user()
    group = create_group(name="Two-up")
    create_membership(group=group, user=other)

    response = client.get(f"/api/v1/user-groups/{group.uid}")
    assert response.json()["member_count"] == 2
