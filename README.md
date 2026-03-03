# Hexagone

Fullstack platform with a FastAPI backend and Astro + React frontend.

## Prerequisites

- Node.js >= 20
- pnpm (via corepack: `corepack enable`)
- Python >= 3.14
- [uv](https://docs.astral.sh/uv/)
- [Lefthook](https://github.com/evilmartians/lefthook)

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

| Command | Description |
|---------|-------------|
| `pnpm -C apps/web dev` | Start dev server |
| `pnpm -C apps/web build` | Build for production |
| `pnpm -C apps/web test` | Run tests (Vitest) |
| `pnpm -C apps/web test:watch` | Run tests in watch mode |
| `pnpm -C apps/web exec biome check .` | Check lint + formatting |
| `pnpm -C apps/web exec biome check --write .` | Auto-fix lint + formatting |

The dev server starts at `http://localhost:4321/`:
- `/` — Static landing page
- `/app` — React SPA (client-side routing)

## API (`apps/backend/`)

Commands run from `apps/backend/`:

| Command | Description |
|---------|-------------|
| `uv sync` | Install dependencies |
| `uv run fastapi dev src/app/main.py` | Start dev server (port 8000) |
| `uv run pytest` | Run tests |
| `uv run ruff check .` | Lint |
| `uv run ruff format --check .` | Check formatting |
| `uv run pyright` | Type checking |

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

Install hooks after cloning:

```bash
lefthook install
```

## Deployment

The frontend builds to static HTML. The hosting provider needs a rewrite rule to support SPA routing:

```
/app/* → /app/index.html
```
