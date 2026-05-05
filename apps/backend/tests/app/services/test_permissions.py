"""Tests for permission filters."""

import pytest

from src.app.repository import (
    EqualsFilter,
    HexClaim,
    HexClaimByCell,
    Upload,
    User,
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


def test_unknown_entity_raises(test_user: User):
    with pytest.raises(
        ValueError, match="No permission filters defined for UserSession"
    ):
        permission_filters(test_user, UserSession)
