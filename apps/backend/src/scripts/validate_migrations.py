"""Validate Alembic migration files.

This pre-commit hook ensures:
1. Migration files are prefixed with 4-digit zero-padded integer values
2. Migrations are numbered according to their Alembic revision chain order
3. No more than one migration per PR
"""

import re
import subprocess
import sys
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

MIGRATIONS_PATH_PREFIX = ("apps", "backend", "src", "alembic", "versions")


def get_ordered_migrations(script_dir: ScriptDirectory) -> list[tuple[str, Path]]:
    """Get migrations in revision chain order using Alembic's API.

    Returns:
        List of tuples containing (filename, filepath) in chain order.
    """
    revisions = list(script_dir.walk_revisions(base="base", head="heads"))
    revisions.reverse()

    return [(Path(rev.path).name, Path(rev.path)) for rev in revisions]


def validate_migration_numbering(
    ordered_migrations: list[tuple[str, Path]],
) -> tuple[bool, str]:
    """Validate that migration filenames are numbered according to chain order.

    Returns:
        Tuple of (is_valid, error_message).
    """
    for i, (filename, _) in enumerate(ordered_migrations, start=1):
        pattern = r"^(\d+)_"
        match = re.match(pattern, filename)

        if not match:
            return False, f"Migration {filename} doesn't have integer prefix"

        file_number = int(match.group(1))
        if file_number != i:
            return (
                False,
                f"Migration {filename} has number {file_number} but should be {i:04d} "
                f"based on revision chain order",
            )

    return True, ""


def get_new_migrations(
    migrations_dir: Path, repo_root: Path, base_branch: str = "main"
) -> list[Path]:
    """Get migration files added in current branch compared to base branch.

    Returns:
        List of new migration file paths, or empty list if unable to determine.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", base_branch],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode != 0:
            return []

        result = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=A", base_branch, "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        if result.returncode != 0:
            return []

        new_files: list[Path] = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            filepath = Path(line)
            if (
                filepath.parts[: len(MIGRATIONS_PATH_PREFIX)] == MIGRATIONS_PATH_PREFIX
                and filepath.suffix == ".py"
            ):
                new_files.append(migrations_dir / filepath.name)

    except subprocess.TimeoutExpired, subprocess.SubprocessError:
        return []
    else:
        return new_files


def main() -> int:
    """Run migration validation checks.

    Returns:
        Exit code: 0 for success, 1 for validation failure.
    """
    backend_root = Path(__file__).parent.parent.parent
    repo_root = backend_root.parent.parent
    migrations_dir = backend_root / "src" / "alembic" / "versions"
    alembic_ini = backend_root / "alembic.ini"

    if not migrations_dir.exists():
        return 0

    config = Config(str(alembic_ini))
    script_dir = ScriptDirectory.from_config(config)

    ordered_migrations = get_ordered_migrations(script_dir)
    if not ordered_migrations:
        return 0

    is_valid, error_msg = validate_migration_numbering(ordered_migrations)
    if not is_valid:
        print(f"ERROR: {error_msg}", file=sys.stderr)
        return 1

    new_migrations = get_new_migrations(migrations_dir, repo_root)
    if len(new_migrations) > 1:
        print("ERROR: More than one migration file per PR", file=sys.stderr)
        print("", file=sys.stderr)
        print("New migrations found:", file=sys.stderr)
        for migration in new_migrations:
            print(f"  - {migration.name}", file=sys.stderr)
        print("", file=sys.stderr)
        print(
            "Please combine these into a single migration or remove extras.",
            file=sys.stderr,
        )
        return 1

    print(f"Migrations validated successfully ({len(ordered_migrations)} total)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
