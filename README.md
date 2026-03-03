# Hexagone

Fullstack platform with a FastAPI backend and Astro + React frontend.

## Prerequisites

- Node.js >= 20
- pnpm (via corepack: `corepack enable`)
- [Lefthook](https://github.com/evilmartians/lefthook)

## Getting Started

```bash
corepack enable
brew install lefthook
pnpm -C apps/web install
lefthook install
```

## Commands

All commands run from the repo root using `pnpm -C apps/web`:

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

## Project Structure

```
hexagone/
├── apps/
│   └── web/                # Astro + React frontend
│       ├── src/
│       │   ├── layouts/    # Astro layouts
│       │   ├── pages/      # Astro pages (index, app shell)
│       │   ├── components/ # Shared React components
│       │   └── app/pages/  # SPA page components
│       ├── public/         # Static assets
│       └── astro.config.mjs
└── lefthook.yml            # Pre-commit hooks
```

## Testing

Tests are co-located with source files (`*.test.tsx`). Uses Vitest + Testing Library + happy-dom.

## Pre-commit Hooks

Lefthook runs on every commit:
- **Biome** — lint + format check on staged files
- **Typecheck** — `astro check` for type errors

Install hooks after cloning:

```bash
lefthook install
```

## Deployment

The frontend builds to static HTML. The hosting provider needs a rewrite rule to support SPA routing:

```
/app/* → /app/index.html
```
