"""Architectural test: service functions must not return Pydantic schemas."""

import importlib
import inspect
import pkgutil
import typing
from types import ModuleType

import src.app.services as services_pkg
from src.app.repository.predicates import Predicate
from src.app.utils.pagination import PaginatedResult
from src.app.utils.schemas import BaseSchema

# BaseSchema subclasses that are internal infrastructure, not response schemas.
ALLOWED_TYPES: set[type] = {PaginatedResult, Predicate}


def _get_all_service_modules() -> list[ModuleType]:
    """Import and return all modules under src.app.services."""
    modules: list[ModuleType] = []
    for info in pkgutil.walk_packages(
        services_pkg.__path__, prefix=services_pkg.__name__ + "."
    ):
        modules.append(importlib.import_module(info.name))
    return modules


def _is_response_schema(tp: object) -> bool:
    """True if *tp* is a BaseSchema subclass that isn't in the allow-list."""
    if not isinstance(tp, type):
        return False
    if not issubclass(tp, BaseSchema) or tp is BaseSchema:
        return False
    return not any(issubclass(tp, allowed) for allowed in ALLOWED_TYPES)


def _return_type_contains_response_schema(annotation: object) -> bool:
    """Check whether a return annotation contains a response-schema type.

    Handles plain types and generics (e.g. PaginatedResult[T], list[T]).
    For generic containers in the allow-list (like PaginatedResult), only
    flags them if a type argument is itself a response schema.
    """
    if annotation is inspect.Parameter.empty or annotation is None:
        return False

    origin = typing.get_origin(annotation)

    # Plain type
    if origin is None:
        return isinstance(annotation, type) and _is_response_schema(annotation)

    # If the origin is an allowed container, check its type args
    if isinstance(origin, type) and origin in ALLOWED_TYPES:
        return any(
            isinstance(arg, type) and _is_response_schema(arg)
            for arg in typing.get_args(annotation)
        )

    # Other generics (list, Union, etc.) — check all args
    for arg in typing.get_args(annotation):
        if _return_type_contains_response_schema(arg):
            return True

    return False


def test_services_do_not_return_pydantic_schemas():
    violations: list[str] = []

    for module in _get_all_service_modules():
        for name, obj in inspect.getmembers(module, inspect.isfunction):
            if name.startswith("_"):
                continue
            if obj.__module__ != module.__name__:
                continue

            hints = typing.get_type_hints(obj)
            ret = hints.get("return")
            if _return_type_contains_response_schema(ret):
                violations.append(f"{module.__name__}.{name} -> {ret}")

    assert violations == [], (
        "Service functions must return ORM instances, not Pydantic schemas:\n"
        + "\n".join(f"  - {v}" for v in violations)
    )
