"""Tests for the table-less Workspace handle and its create policy."""

from collections.abc import Callable

from src.app.repository import BaseModel, ResourceType, Upload, User, UserGroup
from src.app.services.workspace import WORKSPACE, Workspace


def test_workspace_has_no_table():
    """`__abstract__` means the handle maps to no table — no migration, no row."""
    assert "workspace" not in BaseModel.metadata.tables
    assert isinstance(WORKSPACE, Workspace)


def test_creatable_models_each_declare_a_resource():
    """Every creatable model maps to a real ResourceType (the __resource__ contract)."""
    for entity in Workspace.CREATABLE:
        assert isinstance(entity.__resource__, ResourceType)


def test_addressable_models_each_declare_a_resource():
    """Object-level addressable models declare a ResourceType too."""
    for entity in (UserGroup, Upload):
        assert isinstance(entity.__resource__, ResourceType)


def test_permits_create_user_is_admin_only(
    test_user: User,
    create_user: Callable[..., User],
):
    """Creating a User is admin-only; groups and uploads are open to anyone."""
    admin = create_user(email="admin@example.com")
    admin.is_admin = True

    assert Workspace.permits_create(test_user, User) is False
    assert Workspace.permits_create(admin, User) is True

    for entity in (UserGroup, Upload):
        assert Workspace.permits_create(test_user, entity) is True
        assert Workspace.permits_create(admin, entity) is True
