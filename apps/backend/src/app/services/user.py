"""User service for authentication and account management."""

import secrets

from sqlalchemy.exc import IntegrityError

from src.app.repository import (
    Equals,
    Related,
    ScopedRepository,
    Transaction,
    User,
    UserGroup,
)
from src.app.services.password import hash_password, verify_password
from src.app.services.user_group import UserGroupNotFoundError, get_group
from src.app.settings import settings
from src.app.utils import PaginatedResult, SortOrder, get_logger, mask_email

logger = get_logger(__name__)


def get_user_by_email(users: ScopedRepository[User], email: str) -> User | None:
    """Return the user with this email, or None if none exists (or is visible).

    The email filter is gated by the repository: a viewer who can't see a
    user's email can't find that user by it either.
    """
    result = users.get_filtered(
        filters=[Equals(field="email", value=email)],
        page_size=1,
    )
    return result.items[0] if result.items else None


def authenticate_user(
    users: ScopedRepository[User], email: str, password: str
) -> User | None:
    """Authenticate a user by email and password.

    Args:
        users: User repository (system-scoped: there's no viewer yet).
        email: User email address.
        password: Plaintext password to verify.

    Returns:
        The authenticated User, or None if authentication fails.
    """
    user = get_user_by_email(users, email)

    if user is None:
        logger.warning("auth_user_not_found", email=email)
        return None

    if user.archived:
        logger.warning("auth_user_archived", user_uid=user.uid)
        return None

    if not verify_password(password, user.password_hash):
        logger.warning("auth_password_mismatch", user_uid=user.uid)
        return None

    return user


class DuplicateEmailError(Exception):
    """Raised when attempting to create a user with an existing email."""


def create_user(
    users: ScopedRepository[User], tx: Transaction, email: str, password: str
) -> User:
    """Create a new user account.

    Args:
        users: User repository (system-scoped: sign-up has no viewer).
        tx: Transaction boundary.
        email: User email address.
        password: Plaintext password to hash and store.

    Returns:
        The newly created User.

    Raises:
        DuplicateEmailError: If a user with this email already exists.
    """
    try:
        user = _insert_user(users, email, password)
        tx.commit()
    except IntegrityError:
        tx.rollback()
        raise DuplicateEmailError from None

    logger.info("user_created", user_uid=user.uid, email=mask_email(email))
    return user


def _insert_user(users: ScopedRepository[User], email: str, password: str) -> User:
    """Insert a user. Doesn't commit: the caller decides.

    ``create`` flushes, so a duplicate email raises ``IntegrityError`` here.
    """
    return users.create(User(email=email, password_hash=hash_password(password)))


def get_or_create_user_by_email(
    users: ScopedRepository[User], tx: Transaction, email: str
) -> tuple[User, bool]:
    """Fetch the user for *email*, creating one if absent.

    Used by passwordless sign-in: an allow-listed email verifying a magic link
    for the first time gets an account. The user is created with an unusable
    random password placeholder — they have no password and can only sign in
    via magic link. (The ``password_hash`` column is dropped in TASK-0021, at
    which point the placeholder goes away.)

    Returns:
        ``(user, created)`` — ``created`` is True only when a new row was made.
    """
    user = get_user_by_email(users, email)
    if user is not None:
        return user, False

    try:
        user = _insert_user(users, email, secrets.token_urlsafe(32))
        tx.commit()
    except IntegrityError:
        # Lost a create race against a concurrent verify; the row now exists.
        tx.rollback()
        user = get_user_by_email(users, email)
        if user is None:  # pragma: no cover - defensive
            raise
        return user, False

    logger.info("user_created", user_uid=user.uid, email=mask_email(email))
    return user, True


def list_users(
    users: ScopedRepository[User],
    groups: ScopedRepository[UserGroup],
    *,
    group_uid: str,
    page_size: int = settings.DEFAULT_PAGE_SIZE,
    cursor: str | None = None,
) -> PaginatedResult[User]:
    """List users who are members of the given group.

    Raises ``UserGroupNotFoundError`` when the viewer can't see the group —
    the router translates to 404 (no existence leak). Each user's email comes
    back ``REDACTED`` unless the viewer is allowed to see it.
    """
    if get_group(groups, group_uid) is None:
        raise UserGroupNotFoundError(group_uid)

    return users.get_filtered(
        filters=[
            Related(
                field="user_groups",
                inner=Equals(field="uid", value=group_uid),
            ),
        ],
        sort_field=User.uid,
        sort_order=SortOrder.ASC,
        page_size=page_size,
        cursor=cursor,
    )
