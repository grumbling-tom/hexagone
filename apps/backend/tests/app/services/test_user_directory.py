"""The user directory, as seen by Alice: the field-level permission spec.

Rules (``services/permissions.py``):
  1. Anyone can see any user's uid (and when they joined).
  2. A user can see an email only if it's theirs, or they share a live group.
  3. A user can only update their own email.

Cast: Alice (the viewer), Bob (shares a group with Alice), Carol (doesn't).

These are database tests on purpose. Policy behaviour IS query behaviour —
the rules render to SQL — so this is the one place hitting a real database
earns its keep. (SQLite here, not Postgres: EXISTS and boolean columns behave
the same; LIKE collation does not.)
"""

from collections.abc import Callable
from typing import Any

import pytest
from sqlalchemy.orm import Session

from src.app.repository import (
    Equals,
    NotAuthorisedError,
    Or,
    PolicyConflictError,
    ScopedRepository,
    SystemPolicy,
    UnitOfWork,
    UnscopedWriteError,
    UnsortableFieldError,
    User,
    UserGroup,
    UserGroupMembership,
)
from src.app.routers.users import UserResponse
from src.app.services.permissions import ViewerPolicy
from src.app.utils import REDACTED


@pytest.fixture
def cast(
    create_user: Callable[..., User],
    create_group: Callable[..., UserGroup],
    create_membership: Callable[..., UserGroupMembership],
) -> dict[str, User]:
    alice = create_user(email="alice@acme.com")
    bob = create_user(email="bob@acme.com")
    carol = create_user(email="carol@acme.com")

    team = create_group(name="Team", owner=alice)
    create_membership(group=team, user=bob)
    create_group(name="Carol's", owner=carol)

    return {"alice": alice, "bob": bob, "carol": carol}


@pytest.fixture
def alice_users(test_db: Session, cast: dict[str, User]) -> ScopedRepository[User]:
    return ScopedRepository(test_db, User, ViewerPolicy(cast["alice"]))


def one(users: ScopedRepository[User], uid: str) -> User:
    found = users.find_by_uid(uid)
    assert found is not None
    return found


# --- the spec, as a table ------------------------------------------------------


@pytest.mark.parametrize(
    ("subject", "field", "expected"),
    [
        ("alice", "email", "alice@acme.com"),  # (2) it's hers
        ("bob", "email", "bob@acme.com"),  # (2) shared group
        ("carol", "email", REDACTED),  # (2) none of her business
        ("carol", "archived", False),  # (1) visible to anyone
        ("carol", "password_hash", REDACTED),  # never visible to a viewer
    ],
)
def test_alice_sees(
    cast: dict[str, User],
    alice_users: ScopedRepository[User],
    subject: str,
    field: str,
    expected: Any,
):
    user = one(alice_users, cast[subject].uid)
    assert getattr(user, field) == expected


def test_redacted_email_serialises_as_a_marker(
    cast: dict[str, User], alice_users: ScopedRepository[User]
):
    carol = one(alice_users, cast["carol"].uid)
    body = UserResponse.model_validate(carol).model_dump(mode="json")
    assert body == {"uid": carol.uid, "email": {"redacted": True}}


def test_sharing_an_archived_group_does_not_reveal_email(
    test_db: Session,
    cast: dict[str, User],
    alice_users: ScopedRepository[User],
    create_group: Callable[..., UserGroup],
    create_membership: Callable[..., UserGroupMembership],
):
    old = create_group(name="Old", owner=cast["alice"])
    create_membership(group=old, user=cast["carol"])
    ScopedRepository(test_db, UserGroup, SystemPolicy()).update(
        old.uid, {"archived": True}
    )
    test_db.commit()

    assert one(alice_users, cast["carol"].uid).email == REDACTED


# --- the leak: filters are questions -------------------------------------------


def test_cannot_find_a_user_by_an_email_she_cannot_see(
    cast: dict[str, User], alice_users: ScopedRepository[User]
):
    """Without gating, this would return Carol: confirmed, never shown."""
    carol = alice_users.get_filtered([Equals(field="email", value="carol@acme.com")])
    bob = alice_users.get_filtered([Equals(field="email", value="bob@acme.com")])

    assert carol.items == []
    assert [u.uid for u in bob.items] == [cast["bob"].uid]


def test_gating_reaches_inside_or(
    cast: dict[str, User], alice_users: ScopedRepository[User]
):
    result = alice_users.get_filtered(
        [
            Or(
                predicates=[
                    Equals(field="email", value="carol@acme.com"),
                    Equals(field="uid", value=cast["alice"].uid),
                ]
            )
        ]
    )
    assert [u.uid for u in result.items] == [cast["alice"].uid]


def test_cannot_sort_by_a_field_that_can_be_hidden(
    alice_users: ScopedRepository[User],
):
    """ORDER BY email would leak the order of hidden emails."""
    with pytest.raises(UnsortableFieldError):
        alice_users.get_all(sort_field=User.email)


# --- writes --------------------------------------------------------------------


def test_alice_can_update_her_own_email_and_the_result_is_still_masked(
    cast: dict[str, User], alice_users: ScopedRepository[User]
):
    updated = alice_users.update(cast["alice"].uid, {"email": "a@acme.com"})

    assert updated.email == "a@acme.com"
    assert updated.password_hash == REDACTED  # the result goes back to a reader


@pytest.mark.parametrize(
    ("subject", "values"),
    [
        ("bob", {"email": "hijack@acme.com"}),  # (3) not hers
        ("alice", {"password_hash": "x"}),  # her row, but not a writable field
    ],
)
def test_alice_cannot_update(
    cast: dict[str, User],
    alice_users: ScopedRepository[User],
    subject: str,
    values: dict[str, str],
):
    with pytest.raises(NotAuthorisedError):
        alice_users.update(cast[subject].uid, values)


def test_editing_a_loaded_instance_is_refused_at_flush(
    cast: dict[str, User], alice_users: ScopedRepository[User], uow: UnitOfWork
):
    """The ORM would flush this without asking the policy; the guard stops it."""
    bob = one(alice_users, cast["bob"].uid)
    bob.email = "hijack@acme.com"

    with pytest.raises(UnscopedWriteError):
        uow.commit()


# --- one instance, one view ----------------------------------------------------


def test_a_system_read_after_a_masking_read_is_refused(
    test_db: Session, cast: dict[str, User], alice_users: ScopedRepository[User]
):
    """The identity map holds one Carol. Alice's read masked her email; a
    system read in the same session can't un-mask it without leaking it back
    to Alice's reference, and can't keep it masked without lying to the
    system code. So it fails loudly."""
    one(alice_users, cast["carol"].uid)

    with pytest.raises(PolicyConflictError):
        ScopedRepository(test_db, User, SystemPolicy()).find_by_uid(cast["carol"].uid)
