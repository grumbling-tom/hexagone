"""Permission rules for a signed-in viewer: which rows, and which parts of a row.

Two functions, deliberately not one returning a tuple. They answer different
questions — ``row_rules``: "which rows?"; ``field_rules``: "which parts of a
row?" — and keeping them apart is what lets ``gate()`` consult the field rules
without the row rules.

``ViewerPolicy`` binds a user to these rules; ``ScopedRepository`` consults it
on every query. Code with no viewer uses ``SystemPolicy`` instead, and the
entities in ``SYSTEM_ONLY`` have no viewer rules at all.

Every column of every viewer-visible entity has a field rule for READ and for
UPDATE (``test_policy_coverage`` enforces it). A field without a rule is
treated as ``Nobody()``, so forgetting one hides it rather than leaking it.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, overload

from src.app.repository import (
    And,
    Anyone,
    Equals,
    FieldRules,
    HexClaim,
    HexClaimByCell,
    LoginToken,
    Nobody,
    Operation,
    Or,
    Predicate,
    Related,
    Upload,
    UploadStatus,
    User,
    UserGroup,
    UserGroupMembership,
    UserSession,
    queryable_fields,
)
from src.app.repository.database import BaseModel
from src.app.repository.predicates import Guard

__all__ = [
    "SYSTEM_ONLY",
    "Operation",
    "ViewerPolicy",
    "field_rules",
    "row_rules",
]

# Entities only system code touches (sign-in, sessions). They have no viewer
# rules: a ViewerPolicy query against them raises.
SYSTEM_ONLY: frozenset[type[BaseModel]] = frozenset({LoginToken, UserSession})


def _group_readable(user: User) -> Predicate:
    """A UserGroup the user owns or is a member of."""
    return Or(
        predicates=[
            Equals(field="owner_uid", value=user.uid),
            Related(field="members", inner=Equals(field="uid", value=user.uid)),
        ]
    )


@overload
def row_rules(
    user: User,
    entity: type[BaseModel],
    operation: Literal[Operation.CREATE],
) -> list[Guard]: ...


@overload
def row_rules(
    user: User,
    entity: type[BaseModel],
    operation: Literal[Operation.READ, Operation.UPDATE] = ...,
) -> list[Predicate]: ...


def row_rules(  # noqa: PLR0911, PLR0912
    user: User,
    entity: type[BaseModel],
    operation: Operation = Operation.READ,
) -> list[Predicate] | list[Guard]:
    """Return the predicates a row must satisfy for ``user`` to ``operation`` it.

    The overloads carry the operation into the return type: CREATE yields
    ``Guard``s (judged in memory against the instance being inserted),
    READ/UPDATE yield ``Predicate``s (rendered into a WHERE). The
    implementation is only checked against the union, so keep CREATE branches
    to predicates that define ``is_satisfied_by`` (never ``Related``/``Or``).

    Raises:
        ValueError: If no rules are defined for the entity and operation.
    """
    is_me = Equals(field="uid", value=user.uid)
    owns = Equals(field="user_uid", value=user.uid)

    if entity is User:
        if operation is Operation.READ:
            return [Anyone()]  # the directory: everyone is listed
        if operation is Operation.UPDATE:
            return [is_me]

    if entity is UserGroup:
        is_owner = Equals(field="owner_uid", value=user.uid)
        if operation is Operation.READ:
            return [_group_readable(user)]
        if operation in (Operation.CREATE, Operation.UPDATE):
            return [is_owner]

    if entity is UserGroupMembership:
        if operation is Operation.READ:
            return [Related(field="user_group", inner=_group_readable(user))]
        if operation is Operation.CREATE:
            # NOT a real rule. "The viewer owns the group" is a fact about
            # ANOTHER row, and a Guard can only judge the instance in hand. The
            # authority check is `add_member`'s owner-scoped read of the group;
            # the policy can't enforce it. See the note in the PR description.
            return [Anyone()]

    if entity is Upload or entity is HexClaim:
        # Same-row ownership: sound as both a Filter and a Guard.
        if operation is Operation.READ:
            return [owns]
        if operation is Operation.CREATE and entity is Upload:
            return [owns]

    if entity is UploadStatus and operation is Operation.READ:
        # Statuses are created with their Upload (cascade) or by the worker.
        return [Related(field="upload", inner=owns)]

    # A read-only view: readable, but never created or updated.
    if entity is HexClaimByCell and operation is Operation.READ:
        return [owns]

    msg = f"No {operation} permission predicates defined for {entity.__name__}"
    raise ValueError(msg)


def field_rules(
    user: User,
    entity: type[BaseModel],
    operation: Literal[Operation.READ, Operation.UPDATE],
) -> FieldRules:
    """Return, per field, the predicate a row must satisfy to ``operation`` it.

    READ rules become boolean columns selected beside each row; a false one
    masks the field as ``REDACTED``. UPDATE rules are ANDed into the UPDATE's
    WHERE for each field being written. Rules are evaluated against the row
    itself, so they can be relational (``Related``) on both sides.

    Raises:
        ValueError: If no rules are defined for the entity and operation.
    """
    is_me = Equals(field="uid", value=user.uid)
    shares_group = Related(
        field="user_groups",
        inner=And(
            predicates=[
                Equals(field="archived", value=False),
                Related(field="members", inner=is_me),
            ]
        ),
    )

    if entity is User:
        if operation is Operation.READ:
            return {
                "uid": Anyone(),
                "created_at": Anyone(),
                "archived": Anyone(),
                "email": Or(predicates=[is_me, shares_group]),
                "password_hash": Nobody(),
            }
        return {
            "uid": Nobody(),
            "created_at": Nobody(),
            "archived": Nobody(),
            "email": is_me,  # row rule already restricts to is_me; belt and braces
            "password_hash": Nobody(),
        }

    if entity is UserGroup:
        if operation is Operation.READ:
            return {
                "uid": Anyone(),
                "created_at": Anyone(),
                "name": Anyone(),
                "owner_uid": Anyone(),
                "archived": Anyone(),
                "member_count": Anyone(),  # a hybrid: filterable, so it needs a rule
            }
        # The UPDATE row rule already restricts to owners.
        return {
            "uid": Nobody(),
            "created_at": Nobody(),
            "name": Anyone(),
            "owner_uid": Nobody(),
            "archived": Anyone(),
            "member_count": Nobody(),
        }

    if entity is UserGroupMembership:
        return _all(entity, operation)

    if entity in (Upload, UploadStatus, HexClaim, HexClaimByCell):
        return _all(entity, operation)

    msg = f"No {operation} field rules defined for {entity.__name__}"
    raise ValueError(msg)


def _all(
    entity: type[BaseModel], operation: Literal[Operation.READ, Operation.UPDATE]
) -> FieldRules:
    """Every field readable (READ), or none writable (UPDATE).

    For entities whose row rule already says everything about who may see
    them: a row you may read has nothing in it you may not read. Covers
    hybrids too (``Upload.current_status``), which callers filter on.
    """
    rule = Anyone() if operation is Operation.READ else Nobody()
    return dict.fromkeys(queryable_fields(entity), rule)


@dataclass(frozen=True)
class ViewerPolicy:
    """The rules above, bound to the signed-in user."""

    user: User

    @overload
    def rows(
        self, entity: type[BaseModel], operation: Literal[Operation.CREATE]
    ) -> list[Guard]: ...

    @overload
    def rows(
        self,
        entity: type[BaseModel],
        operation: Literal[Operation.READ, Operation.UPDATE],
    ) -> list[Predicate]: ...

    def rows(
        self, entity: type[BaseModel], operation: Operation
    ) -> Sequence[Predicate] | Sequence[Guard]:
        """See ``row_rules``."""
        return row_rules(self.user, entity, operation)

    def fields(
        self,
        entity: type[BaseModel],
        operation: Literal[Operation.READ, Operation.UPDATE],
    ) -> FieldRules:
        """See ``field_rules``."""
        return field_rules(self.user, entity, operation)
