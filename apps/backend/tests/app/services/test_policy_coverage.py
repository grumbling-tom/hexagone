"""Fail closed: every field of every viewer-visible entity has a rule.

A missing rule hides the field (``Nobody()`` is the default), so the failure
mode is "the app is broken", not "the app leaks" — but it's still a bug. This
test makes adding a column without deciding who may see it a test failure.
"""

from typing import Literal

import pytest

from src.app.repository import BaseModel, Operation, User, queryable_fields
from src.app.services.permissions import SYSTEM_ONLY, field_rules, row_rules

VIEWER_ENTITIES = sorted(
    (m.class_ for m in BaseModel.registry.mappers if m.class_ not in SYSTEM_ONLY),
    key=lambda e: e.__name__,
)
SYSTEM_ENTITIES: list[type[BaseModel]] = sorted(SYSTEM_ONLY, key=lambda e: e.__name__)
PROBE = User(uid="__probe__")


@pytest.mark.parametrize("entity", VIEWER_ENTITIES, ids=lambda e: e.__name__)
@pytest.mark.parametrize("operation", [Operation.READ, Operation.UPDATE])
def test_every_field_has_a_rule(
    entity: type[BaseModel], operation: Literal[Operation.READ, Operation.UPDATE]
):
    declared = set(field_rules(PROBE, entity, operation))
    fields = set(queryable_fields(entity))
    assert declared == fields, f"{entity.__name__} {operation}: {declared ^ fields}"


@pytest.mark.parametrize("entity", VIEWER_ENTITIES, ids=lambda e: e.__name__)
def test_every_viewer_entity_is_readable(entity: type[BaseModel]):
    assert row_rules(PROBE, entity, Operation.READ)


@pytest.mark.parametrize("entity", SYSTEM_ENTITIES, ids=lambda e: e.__name__)
def test_system_only_entities_have_no_viewer_rules(entity: type[BaseModel]):
    with pytest.raises(ValueError, match="No read"):
        row_rules(PROBE, entity, Operation.READ)
