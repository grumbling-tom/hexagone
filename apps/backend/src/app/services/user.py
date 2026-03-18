"""User service for account management."""

from sqlalchemy.orm import Session as DBSession

from src.app.repository import EqualsFilter, Repository, User
from src.app.utils import get_logger

logger = get_logger(__name__)


def get_or_create_user(db: DBSession, external_auth_id: str, email: str) -> User:
    """Look up a user by external auth ID, or create one if not found.

    Args:
        db: Database session.
        external_auth_id: Unique ID from the external auth provider.
        email: User email address from the auth provider.

    Returns:
        The existing or newly created User.
    """
    user_repo = Repository(db, User)
    result = user_repo.get_filtered(
        filters=[EqualsFilter(field="external_auth_id", value=external_auth_id)],
        page_size=1,
    )

    if result.items:
        return result.items[0]

    user = User(
        email=email,
        external_auth_id=external_auth_id,
    )
    user_repo.add(user)
    db.commit()
    db.refresh(user)
    logger.info("user_created", user_uid=user.uid, email=email)
    return user
