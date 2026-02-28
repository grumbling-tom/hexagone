# Hexagone

Fullstack platform with a FastAPI backend and Astro + React frontend.

## Prerequisites

- Node.js >= 20
- pnpm (via corepack: `corepack enable`)

## Getting Started

```bash
corepack enable
pnpm install
pnpm dev
```

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
├── biome.json              # Linter/formatter config
├── lefthook.yml            # Pre-commit hooks
└── package.json
```

## Commands

| Command | Description |
|---------|-------------|
| `pnpm dev` | Start dev server |
| `pnpm build` | Build for production |
| `pnpm test` | Run tests (Vitest) |
| `pnpm lint` | Check lint + formatting (Biome) |
| `pnpm lint:fix` | Auto-fix lint + formatting |
| `pnpm format` | Format files |

## Testing

Tests are co-located with source files (`*.test.tsx`). Run with:

```bash
pnpm test              # Single run
pnpm -C apps/web test:watch  # Watch mode
```

Uses Vitest + Testing Library + happy-dom.

## Pre-commit Hooks

Lefthook runs on every commit:
- **Biome** — lint + format check on staged files
- **Typecheck** — `astro check` for type errors

Hooks are installed automatically via the `prepare` script. To manually install:

```bash
pnpm lefthook install
```

## Deployment

The frontend builds to static HTML. The hosting provider needs a rewrite rule to support SPA routing:

```
/app/* → /app/index.html
```
