"""Validate OpenAPI spec conventions."""

import re

from src.app.main import create_app

CAMEL_CASE_RE = re.compile(r"^[a-z][a-zA-Z0-9]*$")

app = create_app()
schema = app.openapi()


def test_all_operations_have_tags():
    """Every route must declare at least one tag so orval generates named modules."""
    violations: list[str] = []

    for path, methods in schema["paths"].items():
        for method, details in methods.items():
            if method in ("parameters", "servers", "summary", "description"):
                continue
            tags = details.get("tags", [])
            if not tags:
                violations.append(f"{method.upper()} {path}")

    assert not violations, (
        "Routes missing tags (will fall into 'default' in generated client):\n"
        + "\n".join(f"  - {v}" for v in violations)
    )


def test_all_operations_have_camel_case_operation_id():
    """Every route must declare an explicit camelCase operation_id."""
    violations: list[str] = []

    for path, methods in schema["paths"].items():
        for method, details in methods.items():
            if method in ("parameters", "servers", "summary", "description"):
                continue
            operation_id = details.get("operationId", "")
            if not CAMEL_CASE_RE.match(operation_id):
                violations.append(f"{method.upper()} {path}: {operation_id!r}")

    assert not violations, (
        "Routes with missing or non-camelCase operation_id:\n"
        + "\n".join(f"  - {v}" for v in violations)
    )
