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

## Router Organisation

One router file per entity in `src/app/routers/`. The router defines paths
relative to its entity name; the version prefix is applied in `main.py`.

- `routers/users.py`          → routes: `/users`, `/users/me`, `/users/{uid}`
- `routers/user_sessions.py`  → routes: `/user-sessions`, `/user-sessions/current`
