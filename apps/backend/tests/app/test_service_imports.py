"""Services reach the database only through ``ScopedRepository``.

A service holding a ``Session`` could run any query SQLAlchemy permits, which
is what the repository exists to prevent. Python can't make ``_db`` truly
private, so this test is the enforcement: no service imports a session, a
query builder, or the session factory, and none reads a repository's ``_db``.
"""

import ast
from pathlib import Path

import pytest

SERVICES = Path(__file__).parents[2] / "src" / "app" / "services"

BANNED_IMPORTS = {
    ("sqlalchemy", "select"),
    ("sqlalchemy", "update"),
    ("sqlalchemy", "delete"),
    ("sqlalchemy", "insert"),
    ("sqlalchemy", "text"),
    ("sqlalchemy.orm", "Session"),
    ("src.app.repository.database", "SessionLocal"),
    ("src.app.repository.database", "get_db"),
    ("src.app.repository.database", "db_session"),
}


@pytest.mark.parametrize("path", sorted(SERVICES.glob("*.py")), ids=lambda p: p.name)
def test_service_has_no_raw_database_access(path: Path):
    tree = ast.parse(path.read_text())
    offences: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            offences += [
                f"from {node.module} import {alias.name}"
                for alias in node.names
                if (node.module, alias.name) in BANNED_IMPORTS
            ]
        if isinstance(node, ast.Attribute) and node.attr == "_db":
            offences.append(f"._db at line {node.lineno}")
    assert offences == []
