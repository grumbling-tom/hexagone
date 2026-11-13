# Hexagone

Turn your runs into territory. Upload a `.gpx` file from a run, and every loop the route closes is filled with [H3](https://h3geo.org/) hexagons that you claim on a map.

A FastAPI backend and a Next.js (React) frontend, backed by Postgres and S3-compatible file storage. New to the project? Start with [docs/hexagone-explained.md](docs/hexagone-explained.md), a plain-English tour of how it all fits together.

## Architecture

```
Browser ──▶ Cloudflare ──▶ cloudflared tunnel ──▶ Web app (Next.js) ──▶ Backend (FastAPI) ──▶ Postgres
   │                                                                          │
   └──────────── uploads .gpx directly via a pre-signed URL ──▶ Tigris ◀───────┘
```

- **Web app** (`apps/web/`) renders every page and calls the backend from the server; the browser never calls the backend directly.
- **Backend** (`apps/backend/`) owns the database and all the rules: sign-in, permissions, uploads and GPX processing.
- **File storage** is S3-compatible: Tigris in production, SeaweedFS locally.
- **Production** runs on k3s on a Mac mini behind a Cloudflare tunnel. Merging to `main` deploys automatically: GitHub Actions builds the images and Argo CD rolls them out. See [infra/k8s/README.md](infra/k8s/README.md) and [docs/gitops-architecture.md](docs/gitops-architecture.md).

### Uploads

1. The browser asks for an upload slot (`POST /api/v1/uploads`). The backend records the upload as `UPLOAD_PENDING` and returns a pre-signed PUT URL plus the headers it requires.
2. The browser uploads the `.gpx` file directly to storage using that URL.
3. `process_upload` (`apps/backend/src/app/services/upload.py`) parses the file, finds closed loops, writes one `hex_claim` row per hexagon, and records `UPLOAD_SUCCESS` or `UPLOAD_INVALID`.

> **Known gap:** nothing triggers step 3 yet. It used to be an S3 event starting an AWS Lambda, which was removed in June 2026; a background worker is planned. Until then, uploads stay at `UPLOAD_PENDING`.

Diagrams and history: [docs/upload-architecture.md](docs/upload-architecture.md). Sign-in: [docs/auth-architecture.md](docs/auth-architecture.md).

## Prerequisites

- Docker, for example via [Colima](https://github.com/abiosoft/colima): `brew install colima docker docker-compose docker-buildx`
- Node.js >= 20 and [pnpm](https://pnpm.io/installation) (`brew install pnpm`, or `corepack enable` on Node versions that still include corepack)
- Python >= 3.14 and [uv](https://docs.astral.sh/uv/)
- [Lefthook](https://github.com/evilmartians/lefthook)

## Getting started

Install dependencies and the commit hooks:

```bash
brew install lefthook
pnpm -C apps/web install
UV_WORKING_DIRECTORY=apps/backend uv sync
lefthook install
```

Run the whole stack in Docker:

```bash
colima start          # if you use Colima
docker compose up -d
```

This starts Postgres, SeaweedFS (plus a one-off job that creates its bucket), a one-off migration job, the backend on port 8000 and the web app on port 3000, with hot reload.

Sign in at `http://localhost:3000/login` as `foo@bar.com`, the only allow-listed address locally. No email is sent in development: the sign-in link is printed in the backend log, and must be opened in the same browser.

```bash
docker compose logs hexagone-backend | grep send_email_console_body
```

Local Postgres is on `localhost:5432`; user, password and database are all `postgres`.

To stop: `docker compose down` (data is kept), then `colima stop`.

## Frontend (`apps/web/`)

Commands run from the repo root using `pnpm -C apps/web`:

| Command                                       | Description                                       |
| --------------------------------------------- | ------------------------------------------------- |
| `pnpm -C apps/web dev`                        | Start dev server                                  |
| `pnpm -C apps/web build`                      | Build for production                              |
| `pnpm -C apps/web test`                       | Run tests (Vitest)                                |
| `pnpm -C apps/web test:watch`                 | Run tests in watch mode                           |
| `pnpm -C apps/web check`                      | Type check (`tsc --noEmit`)                       |
| `pnpm -C apps/web exec biome check .`         | Check lint + formatting                           |
| `pnpm -C apps/web exec biome check --write .` | Auto-fix lint + formatting                        |
| `pnpm -C apps/web lint:imports`               | Check the import rules between features           |
| `pnpm -C apps/web lint:app-structure`         | Check that `app/` holds routing only              |
| `pnpm -C apps/web api:gen-spec`               | Export OpenAPI spec from backend                  |
| `pnpm -C apps/web api:gen-client`             | Generate typed API client from spec               |
| `pnpm -C apps/web api:gen`                    | Generate OpenAPI spec and typed API client        |

Pages at `http://localhost:3000/`:

- `/` — Static landing page (prerendered)
- `/login` — Passwordless sign-in (`/signup` redirects here)
- `/auth/verify` — Where the emailed sign-in link lands
- `/map`, `/uploads`, `/welcome` — Signed-in app pages

To run the dev server outside Docker, start the backend first; the web app proxies `/api` to `http://localhost:8000` by default (see `apps/web/.env.example`).

## Backend (`apps/backend/`)

| Command                                                                                          | Description                  |
| ------------------------------------------------------------------------------------------------ | ---------------------------- |
| `UV_WORKING_DIRECTORY=apps/backend uv sync`                                                      | Install dependencies         |
| `UV_WORKING_DIRECTORY=apps/backend uv run fastapi dev src/app/main.py`                           | Start dev server (port 8000) |
| `cd apps/backend && ENV=TEST uv run pytest`                                                      | Run tests                    |
| `UV_WORKING_DIRECTORY=apps/backend uv run ruff check .`                                          | Lint                         |
| `UV_WORKING_DIRECTORY=apps/backend uv run ruff format --check .`                                 | Check formatting             |
| `UV_WORKING_DIRECTORY=apps/backend uv run pyright`                                               | Type checking                |
| `UV_WORKING_DIRECTORY=apps/backend uv run alembic upgrade head`                                  | Run database migrations      |
| `UV_WORKING_DIRECTORY=apps/backend uv run alembic revision --autogenerate -m "XXXX_description"` | Generate a new migration     |

Tests need `ENV=TEST`: it switches to an in-memory SQLite database and mocked storage, and is how CI runs them. Without it, settings validation stops the run asking for storage credentials.

To run the dev server outside Docker, copy `apps/backend/.env.example` to `apps/backend/.env.development`, the file the backend reads in development. The example points at the Docker Compose Postgres and SeaweedFS, so start those first (`docker compose up -d postgres seaweedfs seaweedfs-init`). With no `DATABASE_URL` set, development falls back to a local SQLite file (`sqlite.db`).

Backend endpoints at `http://localhost:8000/`:

- `/api/health` — Health check
- `/api/v1/...` — The versioned API
- `/docs` — Interactive API docs (Swagger UI)

### Local S3 with SeaweedFS

File uploads use [SeaweedFS](https://github.com/seaweedfs/seaweedfs) (an S3-compatible server) locally; production uses Tigris. SeaweedFS derives a full-admin identity from the `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` env vars set on its container, so pre-signed URLs the backend signs with the same credentials validate. The one-shot `seaweedfs-init` service runs `scripts/seaweedfs-init.sh`, which:

- Creates the `hexagone-gpx-uploads` bucket
- Applies a CORS policy allowing the browser to PUT directly (origins `http://localhost:3000` and `https://hexagone.localhost`)

The backend's `HEXAGONE_S3_ENDPOINT_URL=http://localhost:4566` points pre-signed URLs at SeaweedFS. To upload a file by hand:

```bash
curl -X PUT "<presigned-url>" \
  -H "Content-Type: application/gpx+xml" \
  -H "Content-Length: <size>" \
  --data-binary @route.gpx
```

## Project structure

```
hexagone/
├── apps/
│   ├── web/                    # Next.js (App Router) frontend
│   │   ├── app/                # Routing + app shell (layouts, pages, route groups)
│   │   ├── src/
│   │   │   ├── features/       # Feature-grouped code (components/ + server/)
│   │   │   ├── components/     # Truly shared, generic primitives
│   │   │   ├── config/         # Typed, validated env config
│   │   │   ├── lib/            # Cross-cutting non-React utilities
│   │   │   ├── styles/         # theme.css + main.css (BEM)
│   │   │   └── __generated__/  # Orval-generated API client
│   │   ├── public/             # Static assets
│   │   ├── middleware.ts       # Optimistic auth gate
│   │   └── next.config.mjs
│   └── backend/                # FastAPI API
│       ├── src/
│       │   ├── app/
│       │   │   ├── main.py     # App entry point; registers every router
│       │   │   ├── settings.py # Environment config
│       │   │   ├── routers/    # HTTP endpoints, one file per entity
│       │   │   ├── services/   # Business logic (uploads, GPX processing, sign-in, …)
│       │   │   ├── repository/ # Tables, views, query building
│       │   │   └── utils/      # Logging, pagination, helpers
│       │   └── alembic/        # Database migrations
│       └── tests/
├── infra/
│   ├── k8s/                    # Production manifests (k3s + Argo CD)
│   └── terraform/              # Cloudflare tunnel/DNS and Tigris buckets
├── scripts/                    # prod-stack.sh, local DB ops, gpx_to_h3.py, …
├── docs/                       # Architecture docs
├── docker-compose.yml          # Local stack
└── lefthook.yml                # Pre-commit hooks
```

## Testing

- **Frontend**: Tests are co-located with source files (`*.test.tsx`). Uses Vitest + Testing Library + happy-dom.
- **Backend**: Tests live in `apps/backend/tests/`. Uses pytest + httpx. Run with `ENV=TEST`.

Every pull request runs the pre-commit hooks on all files plus both test suites (`.github/workflows/pr-checks.yml`).

## Pre-commit hooks

Lefthook runs on every commit:

- **API client** — regenerates the OpenAPI spec and typed client
- **Email theme** — regenerates the email colours when `theme.css` changes
- **Biome** and **Prettier** — lint + format staged JS/TS files
- **Typecheck** — `tsc --noEmit` for type errors
- **Import rules** and **app structure** — enforce the frontend folder rules
- **Ruff** — lint + format staged Python files
- **Pyright** — type checking for the API
- **Validate migrations** — checks migration file numbering and the one-per-PR rule

Install hooks after cloning:

```bash
lefthook install
```
