# Backend API Conventions

## URL Structure

All non-infrastructure endpoints are versioned under `/api/v1/`.
Health check is unversioned at `/api/health`.

Endpoints reflect entities with a flat URL structure. Use plural nouns for
resource names. Use hyphens to separate words.

### Good

```
POST   /api/v1/users
GET    /api/v1/users/me
GET    /api/v1/users/{user_uid}
POST   /api/v1/user-sessions
DELETE /api/v1/user-sessions/current
GET    /api/v1/projects/{project_uid}
```

### Bad

```
POST   /api/v1/auth/signup        # verb-oriented, not resource-oriented
POST   /api/v1/auth/login         # verb-oriented
GET    /api/v1/auth/me            # grouped by action, not entity
POST   /api/v1/userSessions       # camelCase
GET    /api/v1/user/session       # singular nouns
DELETE /api/v1/logout             # verb as path segment
```

## Operation IDs

Every FastAPI route must set an explicit `operation_id` in camelCase. This
controls the generated TypeScript hook names (via orval) on the frontend.
Use the pattern `{verb}{Resource}`, e.g.:

```python
@router.get("/health", operation_id="getHealth")
@router.post("/users", status_code=201, operation_id="createUser")
@router.get("/users/current", operation_id="getCurrentUser")
@router.delete("/user-sessions/current", status_code=204, operation_id="deleteCurrentSession")
```

Without an explicit `operation_id`, FastAPI generates verbose IDs like
`health_api_health_get`, which produce clunky hook names like
`useHealthApiHealthGet`.

## Code Sharing

Prefer extracting shared logic into a common module higher in the directory
tree (e.g. `src/app/utils/`) rather than duplicating helper functions across
files. When you see the same function in two or more places, consolidate it.

## Router Tags

Every router must be registered with a `tags` parameter in `main.py`. Orval
uses tags to group generated TypeScript modules — without them, endpoints
fall into a generic `default` module. Use the entity name as the tag:

```python
api_v1_router.include_router(users_router, tags=["users"])
app.include_router(health_router, prefix="/api", tags=["health"])
```

This is enforced by `test_all_operations_have_tags` in `tests/app/test_openapi.py`.

## Router Organisation

One router file per entity in `src/app/routers/`. The router defines paths
relative to its entity name; the version prefix is applied in `main.py`.

- `routers/users.py`          → routes: `/users`, `/users/current`, `/users/{uid}`
- `routers/user_sessions.py`  → routes: `/user-sessions`, `/user-sessions/current`

## Database Migrations

Migration files live in `src/alembic/versions/` and use 4-digit zero-padded
numeric prefixes: `XXXX_descriptive_name.py` (e.g. `0001_add_users_table.py`).

Generate new migrations with:

```
uv run alembic revision --autogenerate -m "XXXX_description"
```

Rules:
- One migration per PR — during development, iterate on the same migration
  rather than creating multiple
- Numbering must match Alembic revision chain order
- Validation is enforced via pre-commit hook (`validate-migrations` in lefthook)

## Authentication

Authentication uses FastAPI dependency injection, not middleware. Routes that
require a logged-in user declare a dependency on `authenticated_user`:

```python
from src.app.dependencies import authenticated_user

@router.get("/things")
def list_things(
    user: Annotated[User, Depends(authenticated_user)],
) -> list[ThingResponse]:
    ...
```

Routes that are public (e.g. registration, login) simply omit the dependency.
Do not use middleware or route-level exemption lists for auth.
