"""Unit tests for ``gate()``: how a caller's filter is pinned to visibility."""

from typing import TYPE_CHECKING

import pytest
from sqlalchemy import ColumnElement, true

from src.app.repository import (
    And,
    Anyone,
    Equals,
    Nobody,
    Operation,
    Or,
    Predicate,
    Related,
    SystemPolicy,
    UnhandledPredicateError,
    User,
    UserGroup,
    gate,
)
from src.app.services.permissions import ViewerPolicy, field_rules, row_rules

if TYPE_CHECKING:
    from src.app.repository import BaseModel

VIEWER = User(uid="viewer")
POLICY = ViewerPolicy(VIEWER)


def test_visible_field_is_left_alone():
    pred = Equals(field="uid", value="x")
    assert gate(pred, User, POLICY) is pred


def test_hideable_field_is_pinned_to_its_read_rule():
    pred = Equals(field="email", value="x@acme.com")
    email_rule = field_rules(VIEWER, User, Operation.READ)["email"]
    assert gate(pred, User, POLICY) == And(predicates=[pred, email_rule])


def test_unknown_field_is_pinned_to_nobody():
    pred = Equals(field="not_a_field", value="x")
    assert gate(pred, User, POLICY) == And(predicates=[pred, Nobody()])


def test_combinators_are_gated_leaf_by_leaf():
    email = Equals(field="email", value="x")
    uid = Equals(field="uid", value="y")
    gated = gate(Or(predicates=[email, uid]), User, POLICY)
    assert gated == Or(predicates=[gate(email, User, POLICY), uid])


def test_related_adds_the_targets_row_rules_and_gates_against_the_target():
    inner = Equals(field="name", value="Team")
    gated = gate(Related(field="user_groups", inner=inner), User, POLICY)
    assert gated == Related(
        field="user_groups",
        inner=And(predicates=[*row_rules(VIEWER, UserGroup), inner]),
    )


def test_constants_pass_through():
    assert gate(Anyone(), User, POLICY) == Anyone()
    assert gate(Nobody(), User, SystemPolicy()) == Nobody()


class Mystery(Predicate):
    def to_sql(self, entity: type[BaseModel]) -> ColumnElement[bool]:
        return true()


def test_unknown_predicate_kind_fails_closed():
    with pytest.raises(UnhandledPredicateError):
        gate(Mystery(), User, POLICY)
