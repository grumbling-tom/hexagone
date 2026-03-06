# Hexagone

Fullstack platform with a FastAPI backend and Astro + React frontend.

## Prerequisites

- Node.js >= 20
- pnpm (via corepack: `corepack enable`)
- Python >= 3.14
- [uv](https://docs.astral.sh/uv/)
- [Lefthook](https://github.com/evilmartians/lefthook)
- [Terraform >= 1.6.0](https://developer.hashicorp.com/terraform/install) (for infrastructure)
- [AWS CLI](https://aws.amazon.com/cli/) (for deployment)

## Getting Started

```bash
corepack enable
brew install lefthook
pnpm -C apps/web install
cd apps/backend && uv sync && cd ../..
lefthook install
```

## Frontend (`apps/web/`)

Commands run from the repo root using `pnpm -C apps/web`:

| Command                                                              | Description                                |
| -------------------------------------------------------------------- | ------------------------------------------ |
| `PUBLIC_BACKEND_BASE_URL=http://localhost:8000 pnpm -C apps/web dev` | Start dev server                           |
| `pnpm -C apps/web build`                                             | Build for production                       |
| `pnpm -C apps/web test`                                              | Run tests (Vitest)                         |
| `pnpm -C apps/web test:watch`                                        | Run tests in watch mode                    |
| `pnpm -C apps/web exec biome check .`                                | Check lint + formatting                    |
| `pnpm -C apps/web exec biome check --write .`                        | Auto-fix lint + formatting                 |
| `pnpm -C apps/web api:gen-spec`                                      | Export OpenAPI spec from backend           |
| `pnpm -C apps/web api:gen-client`                                    | Generate typed API client from spec        |
| `pnpm -C apps/web api:gen`                                           | Generate OpenAPI spec and typed API client |

The dev server starts at `http://localhost:4321/`:

- `/` — Static landing page
- `/app` — React SPA (client-side routing)

## API (`apps/backend/`)

| Command                                                                                | Description                  |
| -------------------------------------------------------------------------------------- | ---------------------------- |
| `UV_PROJECT=apps/backend uv sync`                                                      | Install dependencies         |
| `UV_PROJECT=apps/backend uv run fastapi dev src/app/main.py`                           | Start dev server (port 8000) |
| `UV_PROJECT=apps/backend uv run pytest`                                                | Run tests                    |
| `UV_PROJECT=apps/backend uv run ruff check .`                                          | Lint                         |
| `UV_PROJECT=apps/backend uv run ruff format --check .`                                 | Check formatting             |
| `UV_PROJECT=apps/backend uv run pyright`                                               | Type checking                |
| `UV_PROJECT=apps/backend uv run alembic upgrade head`                                  | Run database migrations      |
| `UV_PROJECT=apps/backend uv run alembic revision --autogenerate -m "XXXX_description"` | Generate a new migration     |

In dev mode (`ENV` unset or `DEV`), the backend uses a local SQLite database (`sqlite.db`) automatically — no external database setup required.

The dev server starts at `http://localhost:8000/`:

- `/health` — Health check endpoint
- `/docs` — Interactive API docs (Swagger UI)

## Project Structure

```
hexagone/
├── apps/
│   ├── web/                  # Astro + React frontend
│   │   ├── src/
│   │   │   ├── layouts/      # Astro layouts
│   │   │   ├── pages/        # Astro pages (index, app shell)
│   │   │   ├── components/   # Shared React components
│   │   │   └── app/pages/    # SPA page components
│   │   ├── public/           # Static assets
│   │   └── astro.config.mjs
│   └── backend/              # FastAPI API
│       ├── src/app/
│       │   ├── main.py       # App entry point
│       │   ├── settings.py   # Environment config
│       │   ├── routers/      # Route handlers
│       │   └── utils/        # Logging, helpers
│       └── tests/
├── terraform/
│   └── production/           # AWS infrastructure (S3, CloudFront, ACM, Route53)
└── lefthook.yml              # Pre-commit hooks
```

## Testing

- **Frontend**: Tests are co-located with source files (`*.test.tsx`). Uses Vitest + Testing Library + happy-dom.
- **API**: Tests live in `apps/backend/tests/`. Uses pytest + httpx.

## Pre-commit Hooks

Lefthook runs on every commit:

- **Biome** — lint + format check on staged JS/TS files
- **Typecheck** — `astro check` for type errors
- **Ruff** — lint + format check on staged Python files
- **Pyright** — type checking for the API
- **Validate migrations** — checks migration file numbering and one-per-PR rule
- **Terraform fmt** — formatting check on `.tf` files
- **Terraform validate** — config validation (requires `terraform init`)

Install hooks after cloning:

```bash
lefthook install
```

## Deployment

Infrastructure is managed with Terraform in `terraform/production/`. See [`terraform/README.md`](terraform/README.md) for full details.

| Command                | Description                                       |
| ---------------------- | ------------------------------------------------- |
| `make deploy-frontend` | Build frontend, sync to S3, invalidate CloudFront |
| `make deploy-backend`  | Build Docker image, push to ECR, update Lambda    |
| `make deploy`          | Deploy both frontend and backend                  |
