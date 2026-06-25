"""User service for authentication and account management."""

import secrets

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DBSession

from src.app.repository import Equals, Related, Repository, User
from src.app.services.password import hash_password, verify_password
from src.app.services.user_group import UserGroupNotFoundError, get_group
from src.app.settings import settings
from src.app.utils import PaginatedResult, SortOrder, get_logger, mask_email

logger = get_logger(__name__)


def get_user_by_email(db: DBSession, email: str) -> User | None:
    """Return the user with this email, or None if none exists."""
    result = Repository(db, User).get_filtered(
        filters=[Equals(field="email", value=email)],
        page_size=1,
    )
    return result.items[0] if result.items else None


def authenticate_user(db: DBSession, email: str, password: str) -> User | None:
    """Authenticate a user by email and password.

    Args:
        db: Database session.
        email: User email address.
        password: Plaintext password to verify.

    Returns:
        The authenticated User, or None if authentication fails.
    """
    user = get_user_by_email(db, email)

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


def create_user(db: DBSession, email: str, password: str) -> User:
    """Create a new user account.

    Args:
        db: Database session.
        email: User email address.
        password: Plaintext password to hash and store.

    Returns:
        The newly created User.

    Raises:
        DuplicateEmailError: If a user with this email already exists.
    """
    user_repo = Repository(db, User)

    user = User(
        email=email,
        password_hash=hash_password(password),
    )

    user_repo.add(user)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DuplicateEmailError from None

    db.refresh(user)
    logger.info("user_created", user_uid=user.uid, email=mask_email(email))
    return user


def get_or_create_user_by_email(db: DBSession, email: str) -> tuple[User, bool]:
    """Fetch the user for *email*, creating one if absent.

    Used by passwordless sign-in: an allow-listed email verifying a magic link
    for the first time gets an account. The user is created with an unusable
    random password placeholder — they have no password and can only sign in
    via magic link. (The ``password_hash`` column is dropped in TASK-0021, at
    which point the placeholder goes away.)

    Returns:
        ``(user, created)`` — ``created`` is True only when a new row was made.
    """
    user = get_user_by_email(db, email)
    if user is not None:
        return user, False

    try:
        return create_user(db, email, secrets.token_urlsafe(32)), True
    except DuplicateEmailError:
        # Lost a create race against a concurrent verify; the row now exists.
        user = get_user_by_email(db, email)
        if user is None:  # pragma: no cover - defensive
            raise
        return user, False


def list_users(
    db: DBSession,
    caller: User,
    *,
    group_uid: str,
    page_size: int = settings.DEFAULT_PAGE_SIZE,
    cursor: str | None = None,
) -> PaginatedResult[User]:
    """List users who are members of the given group.

    Visibility delegates to ``user_group_service.get_group``, which uses
    ``permissions_predicates(caller, UserGroup)`` to permit owner-OR-member
    access. Raises ``UserGroupNotFoundError`` when the caller can see
    neither — the router translates to 404 (no existence leak).
    """
    group = get_group(db, caller, group_uid)
    if group is None:
        raise UserGroupNotFoundError(group_uid)

    return Repository(db, User).get_filtered(
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
