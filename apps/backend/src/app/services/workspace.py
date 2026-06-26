"""The workspace: a table-less handle for collection-level (create) authority.

Object-level capabilities anchor on a row. *Creates* have no row — "may I create
a group?" (any authed user) vs "may I create a user?" (admin only) must be
answerable with no target. ``Workspace`` is that missing target: an abstract
(table-less) ``BaseModel`` subclass with a module-level singleton ``WORKSPACE``,
so it can be passed into ``capabilities_for(db, user, WORKSPACE)`` exactly where
an entity instance would go — one uniform "pass an object" call shape.

Because it has no table, ``Workspace`` can't anchor a relational (``Related``)
predicate, so the one fact a create policy needs — "is this user an admin?" — is
read in memory off the already-loaded actor row (``User.is_admin``), not queried.
"""

from typing import ClassVar

from src.app.repository import BaseModel, Upload, User, UserGroup


class Workspace(BaseModel):
    """Table-less handle for system-wide (collection-level) authority.

    ``__abstract__ = True`` means no table, no migration, no row — yet it's a
    real Python class, so ``WORKSPACE = Workspace()`` is a usable dispatch target.
    """

    __abstract__ = True

    # The models that are "created in the workspace" — the resources a
    # collection-level CREATE capability can be reported for.
    CREATABLE: ClassVar[tuple[type[BaseModel], ...]] = (UserGroup, Upload, User)

    @staticmethod
    def permits_create(user: User, entity: type[BaseModel]) -> bool:
        """Whether ``user`` may create ``entity``.

        Creating a ``User`` is admin-only; groups and uploads are open to any
        authenticated user. Reads ``user.is_admin`` in memory — no query.
        """
        if entity is User:
            return user.is_admin
        return True


WORKSPACE = Workspace()
