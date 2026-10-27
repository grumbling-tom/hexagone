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

Authentication uses FastAPI dependency injection, not middleware. Any route
that injects a viewer-scoped repository (`UserRepo`, `GroupRepo`, … from
`src/app/dependencies.py`) is authenticated by that alone — the repository is
built from `viewer_policy`, which depends on `authenticated_user`. Inject
`authenticated_user` directly only when the route needs the `User` itself
(e.g. as the owner of something it creates):

```python
from src.app.dependencies import ThingRepo

@router.get("/things")
def list_things(things: ThingRepo) -> list[ThingResponse]:
    ...
```

Routes that are public (e.g. registration, login) use `system_scoped(...)`
repositories (`SystemUserRepo`, `SessionRepo`, `LoginTokenRepo`) instead.
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
view becomes the canonical entity; `ScopedRepository`, the permission rules,
and the cursor pipeline all work unchanged.

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
`ScopedRepository.create_many(...)` (which guards each one, then
`session.add_all`s them) rather than dropping to SQLAlchemy Core
(`session.execute(insert(Model), [dict, dict, ...])`).

```python
# Good
new_claims = [
    HexClaim(upload_uid=upload.uid, h3_cell=cell, ...)
    for polygon in polygons
    for cell in polygon.cells
]
claims.create_many(new_claims)

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
use the standard predicates (`In`, `Equals`, etc.) against
that hybrid property.

Push the join/subquery complexity into the model, not into custom filter
classes. This keeps the filter layer simple and composable.

## Service Layer — ScopedRepository Only; Never a Session

Services reach the database **only** through `ScopedRepository[X]` objects
injected by the router, plus a `UnitOfWork` for `commit()`/`rollback()`. A
service never receives a `Session`: one that did could run any query
SQLAlchemy permits. `tests/app/test_service_imports.py` enforces this (no
`Session`/`select`/`update`/… imports in `services/`, no `repo._db`).

A `ScopedRepository` can't be built without a `Policy`, so the permission
rules can't be skipped:

- **Row rules** (`row_rules` in `services/permissions.py`) — which rows the
  viewer may READ / CREATE / UPDATE. ANDed into every query's WHERE (CREATE:
  judged in memory against the instance as `Guard`s).
- **Field rules** (`field_rules`) — which parts of a row. READ rules are
  selected as boolean columns per row; a false one makes the attribute return
  `REDACTED` (serialised as `{"redacted": true}` via `Redactable[T]` in
  `utils/schemas.py`). UPDATE rules ride in the UPDATE's WHERE per field
  written, deny by default.
- **Caller filters are gated** (`repository/gating.py`): each leaf is ANDed
  with its field's READ rule, so a viewer can't *ask* about a field they can't
  see (`?email=carol@…` returns nothing). Sorting is only allowed on fields
  every viewer can see.

### Wiring

```python
# router
@router.patch("/user-groups/{group_uid}", operation_id="updateUserGroup")
def update_user_group(group_uid: str, body: UpdateUserGroupRequest,
                      groups: GroupRepo, uow: UoWDep) -> UserGroupResponse:
    group = user_group_service.update_group(groups, uow, group_uid, name=body.name)
    return UserGroupResponse.model_validate(group)

# service
def update_group(groups: ScopedRepository[UserGroup], uow: UnitOfWork,
                 group_uid: str, *, name: str) -> UserGroup:
    group = groups.update(group_uid, {"name": name})  # owner check is the policy's
    uow.commit()
    return group
```

Viewer-scoped repos come from `scoped(X)`; code with no viewer (sign-up,
sign-in, sessions, the upload worker) uses `system_scoped(X)` /
`SystemPolicy()` — keep every use greppable.

### Writes

- `create(obj)` / `create_many(objs)` — the policy's CREATE `Guard`s judge the
  in-memory instance. Children attached via a cascading relationship
  (`Upload(statuses=[...])`) are inserted under the parent's guard.
- `update(uid, values, where=...)` — atomic; row rules + per-field UPDATE rules
  + your gated `where` in one statement. The result is re-masked.
- `delete(uid)` — atomic; guarded by the UPDATE row rules.

All raise `NotAuthorisedError` (handled app-wide as a 403); none commits.
**Never assign to a loaded instance** (`user.email = "x"`): the session refuses
to flush instance-level edits (`UnscopedWriteError`), because the ORM would
otherwise write them without consulting the policy.

### Adding an entity

1. Model + migration.
2. A `row_rules` branch (READ at least; CREATE/UPDATE only if viewers do them).
3. A `field_rules` branch for READ and UPDATE listing **every** column and
   public hybrid — `test_policy_coverage.py` fails until you do. Or add the
   entity to `SYSTEM_ONLY` if no viewer ever touches it.
4. `ThingRepo = Annotated[ScopedRepository[Thing], Depends(scoped(Thing))]` in
   `dependencies.py`.
5. Services take `things: ScopedRepository[Thing]`; routers inject `ThingRepo`.
6. One table-test row per rule (see `tests/app/services/test_user_directory.py`).

If a predicate you need doesn't exist yet, **add a new `Predicate`
subclass in `repository/predicates.py`** rather than dropping to raw SQL.
A leaf that reads one column subclasses `FieldPredicate` (so `gate()` can pin
it); anything else must be taught to `gate()`, which raises on unknown kinds.
Implement `is_satisfied_by` as well as `to_sql` only when the predicate can be
judged against a single in-memory instance — that is what makes it usable as
a create `Guard`.

**Known limits.**
- Relational CREATE rules can't be `Guard`s ("viewer owns the parent group"
  is a fact about another row). `UserGroupMembership` CREATE is `Anyone()`;
  `add_member`'s owner-scoped read is the real check.
- Relationships loaded by their own default loaders (`Upload.statuses`,
  `UserSession.user`, `UserGroupMembership.user`) bypass the policy.
- Masks live on identity-map instances. One session serves one view; a
  system read of a row a viewer read masked raises `PolicyConflictError`.

**Exceptions — raw `select(...)` is appropriate only** inside a `View`
subclass's `__view_selectable__` and model `@hybrid_property` expressions.

## Service Layer — Workhorse `list_<things>` + Thin `get_<thing>` Wrapper

When a service exposes both "list" and "fetch one of those things" for
the same entity, write **one** `list_<things>` function that builds the
filter list (archived check, scoping flags) and returns
`PaginatedResult[Thing]`. Then make `get_<thing>` a one-line wrapper that
delegates to it with a `uid` filter and returns the first item — the filter
logic lives in one place and is exercised by both endpoints. (Permission
scoping isn't in the filter list any more — the repository applies it.)

### Good

```python
def list_groups(
    groups: ScopedRepository[UserGroup], *,
    page_size=settings.DEFAULT_PAGE_SIZE,
    group_uid=None,
    operation=Operation.READ,
) -> PaginatedResult[UserGroup]:
    filters: list[Predicate] = [Equals(field="archived", value=False)]
    if operation is Operation.UPDATE:
        filters.extend(groups.policy.rows(UserGroup, Operation.UPDATE))
    if group_uid is not None:
        filters.append(Equals(field="uid", value=group_uid))
    return groups.get_filtered(filters=filters, ...)


def get_group(groups, group_uid, operation=Operation.READ) -> UserGroup | None:
    try:
        return list_groups(groups, group_uid=group_uid, operation=operation).items[0]
    except IndexError:
        return None
```

### Bad — duplicated filter logic

```python
def get_group(groups, group_uid):
    # Same filter list, restated by hand — drifts the moment list_groups grows a clause:
    return groups.get_filtered(
        filters=[Equals(field="archived", value=False),
                 Equals(field="uid", value=group_uid)],
    ).items[0]
```

Express access modifiers through the `operation` argument (e.g.
`get_group(..., operation=Operation.UPDATE)` narrows to groups the viewer may
change) rather than ad-hoc flags like `owner_only=True`, so the rule lives in
the permissions layer.

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
def get_group(groups, group_uid) -> UserGroup | None:
    try:
        return list_groups(groups, group_uid=group_uid).items[0]
    except IndexError:
        return None

# router
group = user_group_service.get_group(groups, group_uid)
if group is None:
    raise HTTPException(status_code=404, detail="Group not found")
```

### Bad — exception flow for "not found"

```python
# service
def get_group(groups, group_uid) -> UserGroup:
    group = ...
    if group is None:
        raise UserGroupNotFoundError(group_uid)
    return group

# router has to catch what the service threw
try:
    group = user_group_service.get_group(groups, group_uid)
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
def update_group(groups, uow, group_uid, *, name) -> UserGroup:
    group = get_group(groups, group_uid, operation=Operation.UPDATE)
    if group is None:
        raise UserGroupNotFoundError(group_uid)
    ...
```

— the wrapper still returns `None`, the mutation service raises
explicitly, and the router catches the mutation-specific exceptions.
