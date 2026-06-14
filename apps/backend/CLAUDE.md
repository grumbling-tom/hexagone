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

### Filter related entities with query parameters, not URL nesting

When listing the children of a parent entity, expose the parent's
identifier as a query parameter on the child collection rather than
nesting the child under the parent's URL.

#### Good

```
GET /api/v1/users?group_uid={group_uid}        # users in a group
GET /api/v1/hex-claims?upload_uid={upload_uid} # claims from an upload
```

#### Bad

```
GET /api/v1/user-groups/{group_uid}/members    # nested under parent
GET /api/v1/uploads/{upload_uid}/hex-claims    # nested under parent
```

The query-param shape keeps the resource collection's URL stable
regardless of how the caller is filtering, makes additional filters
composable (`?group_uid=X&archived=true`), and avoids parallel routes
that return the same shape from different paths.

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

## Logging Around External Service Calls

Every call to an external service (HTTP API, email provider, S3, etc.) must be
bracketed by `structlog` log statements: an `info` line **before** the call
describing the intent and an `info` line **after** a successful call (including
any returned id). Failures should surface via `logger.exception(...)` at the
call site that handles them. This gives every outbound dependency call a
traceable request/response pair in the logs. See `ResendEmailClient.send` in
`services/email.py` for the canonical example.

**Never log raw PII.** Don't put plaintext emails (or message bodies that embed
them), tokens, or secrets in logs. Prefer the non-PII `user_uid` as the
identifier; when an email must appear, mask it with `mask_email()` from
`src.app.utils` (`t***@gmail.com`). This follows the existing `hash_user_agent`
precedent in `services/user_session.py`.

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

## Service File Naming

Files in `src/app/services/` are named for the **noun** the service is built
around — the entity or domain it operates on — never the action it performs.
The file names the thing; the functions inside carry the verbs.

### Good

```
services/gpx.py        # GpxValidationError, gpx_bytes_to_polygons
services/upload.py     # create_upload, process_upload, list_uploads
services/storage.py    # StorageBackend, S3StorageBackend
```

### Bad

```
services/gpx_processing.py   # action in the filename
services/upload_service.py   # redundant "_service" suffix
services/process_upload.py   # a verb as the filename
```

When two files would name the same noun (e.g. CRUD and a processing pipeline
for uploads), keep them in the **one** noun-named file rather than splitting by
action — see `services/upload.py`, which holds both `create_upload` and
`process_upload`.

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

### Database Views

When a PR introduces a `View` subclass (see "View-Backed Models" below),
the same migration that adds the underlying table also creates the view.
Use the `create_view_ddl` / `drop_view_ddl` helpers so the migration reads
the name and SELECT from the same source as the runtime registration:

```python
from src.app.repository.views import (
    HexClaimByCell, create_view_ddl, drop_view_ddl,
)

def upgrade() -> None:
    # ... CREATE TABLE for the underlying entity ...
    op.execute(create_view_ddl(HexClaimByCell))

def downgrade() -> None:
    op.execute(drop_view_ddl(HexClaimByCell))
    # ... DROP TABLE for the underlying entity ...
```

The in-memory SQLite test DB picks up the view automatically via the
`view()` helper's metadata event listeners — no `conftest.py` changes
required.

## Query Parameters

Define query parameters as a Pydantic schema (inheriting `BaseSchema`) and
inject with `Annotated[MyParams, Query()]`. Use `Query()`, **not** `Depends()`,
so FastAPI correctly parses list query params (e.g. `?statuses=A&statuses=B`).

```python
from fastapi import Query
from pydantic import Field

class ListThingsParams(BaseSchema):
    page_size: int = Field(default=settings.DEFAULT_PAGE_SIZE, gt=0, le=100)
    cursor: str | None = Field(default=None)
    statuses: list[StatusEnum] | None = Field(default=None)

@router.get("/things")
def list_things(
    params: Annotated[ListThingsParams, Query()],
) -> PaginatedResult[ThingResponse]:
    ...
```

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

## Testing — Fixtures over Helper Functions

Use `pytest.fixture` factories (defined in `conftest.py`) for test data
setup, not private `_create_*` helper functions. Fixtures integrate with
pytest's dependency injection, are automatically discovered, and can be
shared across test modules.

### Good

```python
# conftest.py
@pytest.fixture
def create_upload(test_db: Session, test_user: User) -> Callable[..., Upload]:
    def _factory(filename: str, *, file_size: int = 100) -> Upload:
        upload = Upload(user_uid=test_user.uid, original_filename=filename, ...)
        ...
        return upload
    return _factory

# test_uploads.py
def test_filter_by_name(test_db: Session, create_upload: Callable[..., Upload]):
    create_upload("alpha.gpx")
    create_upload("beta.gpx")
    ...
```

### Bad

```python
# test_uploads.py
def _create_upload(db: Session, user: User, filename: str) -> Upload:
    upload = Upload(user_uid=user.uid, original_filename=filename, ...)
    ...
    return upload

def test_filter_by_name(test_db: Session, test_user: User):
    _create_upload(test_db, test_user, "alpha.gpx")
    _create_upload(test_db, test_user, "beta.gpx")
    ...
```

## Service Layer — Return ORM Instances

Service functions (`src/app/services/`) must return ORM model instances,
primitives, or `PaginatedResult[OrmModel]` — never Pydantic response
schemas. The router layer converts ORM instances into response schemas.

Enforced by `test_services_do_not_return_pydantic_schemas` in
`tests/app/test_service_returns.py`.

## View-Backed Models for Aggregated Endpoints

When the response shape doesn't map 1:1 to a base table — typically
aggregations, rollups, or projections — define a **view-backed ORM model**
rather than hand-rolling `select(...).group_by(...)` in the service. The
view becomes the canonical entity; `Repository`, `permission_filters`, and
the cursor pipeline all work unchanged.

All view-backed models live in `repository/views.py` and inherit from the
abstract `View` base. The pattern is adapted from the SQLAlchemy wiki Views
recipe ([sqlalchemy/sqlalchemy/wiki/Views](https://github.com/sqlalchemy/sqlalchemy/wiki/Views))
— the link is reproduced as a comment in `views.py` so future maintainers
can verify against the source.

Each subclass declares:
- `__view_selectable__`: a SQLAlchemy `select(...)` whose columns include
  synthetic `uid` (made unique via column concatenation, e.g.
  `col_a + literal(":") + col_b`) and `created_at` (e.g.
  `func.min(<timestamp_col>)`) to satisfy `BaseModel`'s requirements.
- `__table__ = view("<name>", BaseModel.metadata, __view_selectable__)`.

See `HexClaimByCell` in `repository/views.py` for the canonical example.

The view is created in production by the migration that adds the
underlying table (see "Database Views" under "Database Migrations" above)
and in the test DB automatically via the `view()` helper's metadata event
listeners.

## Bulk Inserts — Use ORM Instances + `session.add_all`

When inserting multiple rows, build ORM model instances and pass them to
`session.add_all(...)` rather than dropping to SQLAlchemy Core
(`session.execute(insert(Model), [dict, dict, ...])`).

```python
# Good
claims = [
    HexClaim(upload_uid=upload.uid, h3_cell=cell, ...)
    for polygon in polygons
    for cell in polygon.cells
]
db.add_all(claims)

# Bad
rows = [
    {"upload_uid": upload.uid, "h3_cell": cell, ...}
    for polygon in polygons
    for cell in polygon.cells
]
db.execute(insert(HexClaim), rows)
```

ORM instances + `add_all` keep `BaseModel` defaults (UUID v7 `uid`,
`created_at`) and any `__init__`/event-listener behaviour intact, and the
constructed objects are typed against the model rather than untyped dicts.
Reach for Core inserts only if profiling shows the unit-of-work overhead
is a real bottleneck.

## Filtering on Related Models

When you need to filter a model based on values in a related model (e.g.
filtering uploads by their latest status), use a `@hybrid_property` on the
parent model with a `@expression` that returns a correlated subquery. Then
use the standard filter classes (`InFilter`, `EqualsFilter`, etc.) against
that hybrid property.

Push the join/subquery complexity into the model, not into custom filter
classes. This keeps the filter layer simple and composable.

## Service Layer — Use Repository + Filter Classes for Queries

Service queries access the database through `Repository(db, Model)` plus
the type-safe `Filter` classes in `repository/filters.py`, composing with
`permission_filters(user, entity)` from `services/permissions.py` where
authorisation applies. Avoid raw `select(...)` for service queries — it
bypasses cursor pagination, the composable Filter contract, and the
single central permissions layer.

### Good

```python
def list_groups_for_user(db, user) -> list[UserGroup]:
    return Repository(db, UserGroup).get_filtered(
        filters=[
            *permission_filters(user, UserGroup),
            EqualsFilter(field="archived", value=False),
        ],
        sort_field=UserGroup.created_at,
        sort_order=SortOrder.DESC,
    ).items
```

### Bad

```python
def list_groups_for_user(db, user) -> list[UserGroup]:
    stmt = (
        select(UserGroup)
        .join(UserGroupMembership, ...)
        .where(...)
    )
    return list(db.execute(stmt).scalars().all())
```

If a filter you need doesn't exist yet, **add a new `Filter` subclass in
`repository/filters.py`** rather than dropping to raw SQL. Filters are
reusable, unit-testable, and compose with `Repository.get_filtered`.

**Exceptions — raw `select(...)` is appropriate when:**
- Aggregates `Repository` doesn't expose — `func.count(...)`,
  `func.sum(...)`, etc.
- Inside a `View` subclass's `__view_selectable__`.
- The query target genuinely requires multiple entities back in one
  round-trip (rare; prefer two `Repository.find_by_uid()` calls unless
  profiling shows a real cost).

Note: this section is about *queries*. Writes (`db.add`, `db.delete`,
attribute mutation followed by `db.commit`) go through the session
directly — `Repository` is a query helper, not a unit-of-work wrapper.

## Service Layer — Workhorse `list_<things>` + Thin `get_<thing>` Wrapper

When a service exposes both "list" and "fetch one of those things" for
the same entity, write **one** `list_<things>` function that builds the
filter list (including `permission_filters`, archived check, scoping
flags) and returns `PaginatedResult[Thing]`. Then make `get_<thing>` a
one-line wrapper that delegates to it with a `uid` filter and returns
the first item — the filter logic, including any auth scoping, lives in
one place and is exercised by both endpoints.

### Good

```python
def list_groups(  # noqa: PLR0913
    db, user, *,
    page_size=settings.DEFAULT_PAGE_SIZE,
    group_uid=None,
    owner_only=False,
    sort_field="created_at",
    sort_order=SortOrder.DESC,
) -> PaginatedResult[UserGroup]:
    filters = [
        *permission_filters(user, UserGroup),
        EqualsFilter(field="archived", value=False),
    ]
    if owner_only:
        filters.append(EqualsFilter(field="owner_uid", value=user.uid))
    if group_uid is not None:
        filters.append(EqualsFilter(field="uid", value=group_uid))
    return Repository(db, UserGroup).get_filtered(filters=filters, ...)


def get_group(db, user, group_uid, *, owner_only=False) -> UserGroup | None:
    try:
        return list_groups(
            db, user, group_uid=group_uid, owner_only=owner_only,
        ).items[0]
    except IndexError:
        return None
```

### Bad — duplicated filter logic

```python
def list_groups(db, user):
    return Repository(db, UserGroup).get_filtered(
        filters=[*permission_filters(user, UserGroup),
                 EqualsFilter(field="archived", value=False)],
    )

def get_group(db, user, group_uid):
    # Same filter list, restated by hand — drifts the moment list_groups grows a clause:
    return Repository(db, UserGroup).get_filtered(
        filters=[*permission_filters(user, UserGroup),
                 EqualsFilter(field="archived", value=False),
                 EqualsFilter(field="uid", value=group_uid)],
    ).items[0]
```

Scoping flags like `owner_only=True` are how access modifiers get
expressed today — they layer an extra filter onto the read permission
set. When `permission_filters(user, entity, operation)` lands
(operation ∈ {READ, UPDATE, DELETE, …}), these flags can move into the
permissions layer.

## Service Layer — Return `None` for Absence; Routers Raise HTTP

Service "fetch one" functions return the entity or `None` when not
found/not visible — they **don't** raise a custom `*NotFoundError`. The
router translates `None` into the right HTTP response (usually 404).

Why: services compose with other services and with tests. Forcing every
caller through a try/except for "not found" leaks routing concerns into
the service layer and makes simple cases like "delete if exists" noisy.

### Good

```python
# service
def get_group(db, user, group_uid) -> UserGroup | None:
    try:
        return list_groups(db, user, group_uid=group_uid).items[0]
    except IndexError:
        return None

# router
group = user_group_service.get_group(db, user, group_uid)
if group is None:
    raise HTTPException(status_code=404, detail="Group not found")
```

### Bad — exception flow for "not found"

```python
# service
def get_group(db, user, group_uid) -> UserGroup:
    group = ...
    if group is None:
        raise UserGroupNotFoundError(group_uid)
    return group

# router has to catch what the service threw
try:
    group = user_group_service.get_group(db, user, group_uid)
except user_group_service.UserGroupNotFoundError:
    raise HTTPException(status_code=404, ...) from None
```

Exceptions are still appropriate for **business-rule violations** —
writes the caller couldn't avoid by branching, like
`DuplicateMembershipError` (uniqueness conflict during an insert) or
`UserGroupNotFoundError` raised from a *mutation* service function
(`update_group`, `archive_group`) where there's no sensible "no-op on
missing" semantics. The pattern then looks like:

```python
def update_group(db, user, group_uid, *, name) -> UserGroup:
    group = get_group(db, user, group_uid, owner_only=True)
    if group is None:
        raise UserGroupNotFoundError(group_uid)
    ...
```

— the wrapper still returns `None`, the mutation service raises
explicitly, and the router catches the mutation-specific exceptions.
