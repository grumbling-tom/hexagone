# Hexagone

Fullstack platform with a FastAPI backend and Next.js (React) frontend.

## Prerequisites

- Node.js >= 20
- pnpm (via corepack: `corepack enable`)
- Python >= 3.14
- [uv](https://docs.astral.sh/uv/)
- [Lefthook](https://github.com/evilmartians/lefthook)

## Getting Started

For local application development:

```bash
corepack enable
brew install lefthook
pnpm -C apps/web install
UV_WORKING_DIRECTORY=apps/backend uv sync
lefthook install
```

## Frontend (`apps/web/`)

Commands run from the repo root using `pnpm -C apps/web`:

| Command                                       | Description                                |
| --------------------------------------------- | ------------------------------------------ |
| `pnpm -C apps/web dev`                        | Start dev server                           |
| `pnpm -C apps/web build`                      | Build for production                       |
| `pnpm -C apps/web test`                       | Run tests (Vitest)                         |
| `pnpm -C apps/web test:watch`                 | Run tests in watch mode                    |
| `pnpm -C apps/web exec biome check .`         | Check lint + formatting                    |
| `pnpm -C apps/web exec biome check --write .` | Auto-fix lint + formatting                 |
| `pnpm -C apps/web api:gen-spec`               | Export OpenAPI spec from backend           |
| `pnpm -C apps/web api:gen-client`             | Generate typed API client from spec        |
| `pnpm -C apps/web api:gen`                    | Generate OpenAPI spec and typed API client |

The dev server starts at `http://localhost:3000/`:

- `/` — Static landing page (prerendered)
- `/login`, `/signup` — Auth pages
- `/map`, `/uploads`, `/welcome` — Auth-gated app routes

## API (`apps/backend/`)

| Command                                                                                          | Description                  |
| ------------------------------------------------------------------------------------------------ | ---------------------------- |
| `UV_WORKING_DIRECTORY=apps/backend uv sync`                                                      | Install dependencies         |
| `UV_WORKING_DIRECTORY=apps/backend uv run fastapi dev src/app/main.py`                           | Start dev server (port 8000) |
| `UV_WORKING_DIRECTORY=apps/backend uv run pytest`                                                | Run tests                    |
| `UV_WORKING_DIRECTORY=apps/backend uv run ruff check .`                                          | Lint                         |
| `UV_WORKING_DIRECTORY=apps/backend uv run ruff format --check .`                                 | Check formatting             |
| `UV_WORKING_DIRECTORY=apps/backend uv run pyright`                                               | Type checking                |
| `UV_WORKING_DIRECTORY=apps/backend uv run alembic upgrade head`                                  | Run database migrations      |
| `UV_WORKING_DIRECTORY=apps/backend uv run alembic revision --autogenerate -m "XXXX_description"` | Generate a new migration     |

In dev mode (`ENV` unset or `DEV`), the backend uses a local SQLite database (`sqlite.db`) automatically — no external database setup required.

### Local S3 with SeaweedFS

File uploads use [SeaweedFS](https://github.com/seaweedfs/seaweedfs) (an S3-compatible server) for local development; production uses Tigris. Start it with docker compose:

```bash
docker compose up seaweedfs seaweedfs-init
```

SeaweedFS derives a full-admin identity from the `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` env vars set on its container, so presigned URLs the backend signs with the same credentials validate. The one-shot `seaweedfs-init` service then runs `scripts/seaweedfs-init.sh`, which:

- Creates the `hexagone-gpx-uploads` S3 bucket
- Applies a CORS policy allowing the browser to PUT directly (origins `http://localhost:3000` and `https://hexagone.localhost`)

The backend reads `HEXAGONE_S3_ENDPOINT_URL=http://localhost:4566` from `.env`, so pre-signed URLs point at SeaweedFS. Upload files with curl:

```bash
curl -X PUT "<presigned-url>" \
  -H "Content-Type: application/gpx+xml" \
  -H "Content-Length: <size>" \
  --data-binary @route.gpx
```

The dev server starts at `http://localhost:8000/`:

- `/health` — Health check endpoint
- `/docs` — Interactive API docs (Swagger UI)

## Upload Architecture

The GPX upload flow uses presigned S3 URLs and event-driven processing:

![Upload Architecture](docs/upload-architecture.excalidraw)

1. Browser requests a presigned upload URL via `POST /api/v1/uploads`
2. Backend Lambda generates a presigned PUT URL and returns it with required headers
3. Browser uploads the `.gpx` file directly to S3 using the presigned URL
4. S3 `ObjectCreated` event triggers the Upload Processor Lambda
5. Processor downloads the file, parses the GPX, and updates the status in PostgreSQL

## Project Structure

```
hexagone/
├── apps/
│   ├── web/                  # Next.js (App Router) frontend
│   │   ├── app/              # Routing + app shell (layouts, pages, route groups)
│   │   ├── src/
│   │   │   ├── features/     # Feature-grouped code (components/ + server/)
│   │   │   ├── components/   # Truly shared, generic primitives
│   │   │   ├── config/       # Typed, validated env config
│   │   │   ├── lib/          # Cross-cutting non-React utilities
│   │   │   ├── styles/       # theme.css + main.css (BEM)
│   │   │   └── __generated__/ # Orval-generated API client
│   │   ├── public/           # Static assets
│   │   ├── middleware.ts     # Optimistic auth gate
│   │   └── next.config.mjs
│   └── backend/              # FastAPI API
│       ├── src/app/
│       │   ├── main.py       # App entry point
│       │   ├── settings.py   # Environment config
│       │   ├── routers/      # Route handlers
│       │   └── utils/        # Logging, helpers
│       └── tests/
└── lefthook.yml              # Pre-commit hooks
```

## Testing

- **Frontend**: Tests are co-located with source files (`*.test.tsx`). Uses Vitest + Testing Library + happy-dom.
- **API**: Tests live in `apps/backend/tests/`. Uses pytest + httpx.

## Pre-commit Hooks

Lefthook runs on every commit:

- **Biome** — lint + format check on staged JS/TS files
- **Typecheck** — `tsc --noEmit` for type errors
- **Ruff** — lint + format check on staged Python files
- **Pyright** — type checking for the API
- **Validate migrations** — checks migration file numbering and one-per-PR rule

Install hooks after cloning:

```bash
lefthook install
```
