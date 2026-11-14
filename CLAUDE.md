# Project Guidelines

## Package Manager

Use `pnpm` exclusively. Never use `npm` or `npx`.

## Frontend File Organisation

Code under `apps/web/src/` is grouped by **feature**, not by file type. New components default to a feature folder; only promote to top-level `components/` once something is genuinely reused across features.

The **Next.js App Router** lives at `apps/web/app/` (project root, *outside* `src/`) and is reserved for **routing**: Next's file conventions (`layout.tsx`, `page.tsx`, route segments, route groups like `(authed)/`) plus app chrome (`Nav.tsx`). Route files stay thin and compose feature components and feature Server Actions. **No `actions.ts` under `app/`** — Server Actions are feature code and live in `features/<x>/server/` (a route imports them, it doesn't define them). This is enforced by `pnpm lint:app-structure`. Static routes are prerendered at build; the image runs the standalone Node server (`output: "standalone"`, which also proxies `/api` to the backend).

A feature folder splits into two subfolders: `components/` (UI) and `server/` (`'use server'` Server Actions). Anything genuinely shared *within* the feature by both (e.g. a `types.ts`) sits at the feature root.

```
apps/web/
  app/                  Routing + app shell (Next App Router; project root)
    layout.tsx          Root layout: <html>, fonts, global CSS
    page.tsx            '/' landing — static, prerendered
    Nav.tsx             Top nav (app chrome)
    login/page.tsx      '/login' — imports LoginForm + login action from features/auth
    signup/page.tsx     '/signup'
    (authed)/           Route group (no URL segment) — auth-gated area
      layout.tsx        'use client' — auth guard + <Nav>
      map/page.tsx      '/map'
      uploads/page.tsx  '/uploads'
      welcome/page.tsx  '/welcome' — new-user onboarding
  src/                  Feature-grouped, non-routing code (imported via @/)
    features/             One folder per domain feature
      uploads/
        components/       UI: UploadList, UploadForm, UploadModal, …
        server/           'use server' actions: uploads.ts (requestUpload, …)
      auth/
        components/       LoginForm, SignupForm
        server/           login.ts, signup.ts, logout.ts
        types.ts          shared within the feature (AuthFormState)
      hexMap/
        components/       Map view (HexMap, EmptyMap)
      onboarding/
        components/       OnboardingChoices
        server/           finishOnboarding.ts
    components/           Truly shared, generic primitives (e.g. Button) — empty until needed
    config/               env.ts — typed, validated environment config (see below)
    lib/                  Cross-cutting non-React utilities (fetch client, etc.)
    styles/               theme.css + main.css (see CSS section below)
    __generated__/        Orval-generated API client — do not edit by hand
```

Route files in `app/` import `src/` code via the `@/` alias (the alias only maps to `src/`). Everything under `src/` stays organised by feature.

**Auth gating.** `apps/web/middleware.ts` is the primary gate: it does an optimistic presence check on the opaque, httpOnly `sessionid` cookie and server-side-redirects unauthed requests to the protected routes (`/map`, `/uploads`) to `/login` — no flash, no protected shell shipped. It can't *validate* the cookie (the backend owns that), so the `(authed)/` client layout is the backstop for a present-but-invalid/expired cookie, and the backend is the real authority (it 401s every `/api` call). Don't gate `/login`/`/signup` in middleware — with a presence-only check that can loop against the layout backstop.

**Where to put a new file**:
- A feature UI component → `features/<feature>/components/`
- A feature Server Action → `features/<feature>/server/`
- Part of the app chrome or routing (`page.tsx`, `layout.tsx`, `Nav.tsx`) → `app/`
- Reused across two or more features → `components/`
- Non-React utility → `lib/`

**Imports**: always use the `@/` alias (mapped to `src/`). Do not use deep relative paths like `../../features/uploads/UploadList`.

### Environment Configuration

Never read `process.env` directly. All environment configuration goes through the typed, validated schema in `src/config/env.ts` (`@t3-oss/env-nextjs` + zod — the Next.js analogue of the backend's pydantic-settings `Settings`). Import `{ env }` from `@/config/env` and read `env.MY_VAR`; the schema is the single source of truth for what config exists and what shape it has, and it fails loudly at boot/build on anything missing or malformed.

To add a var: declare it under `server` (or `client` for `NEXT_PUBLIC_*` vars, which must also be listed in `experimental__runtimeEnv`). Give it a zod schema with a sensible `.default(...)` where one exists. For booleans use enum-then-transform (`z.enum(["true","false"]).default("false").transform((v) => v === "true")`), **not** `z.coerce.boolean()` — under `coerce` the string `"false"` coerces to `true`. The `@/config/env` import works from root-level files like `instrumentation.ts` and `middleware.ts` too, not just `src/`.

### Frontend Import Rules

Adapted from [bulletproof-react](https://github.com/alan2207/bulletproof-react/blob/master/docs/project-structure.md). Enforced by `pnpm lint:imports` (script at `apps/web/scripts/check-imports.mjs`) and `pnpm lint:app-structure` (`apps/web/scripts/check-app-structure.mjs`), both run on pre-commit via lefthook.

Three rules:

1. **No cross-feature imports.** A file in `features/uploads/` may not import from `features/map/`. Compose features at the page/app layer instead.
2. **Unidirectional layers.** Code flows `shared → features → app`, never the other way:

   | From ↓ \ To →             | `app/` | `features/` | shared (`components`, `hooks`, `lib`, `types`, `utils`) |
   | ------------------------- | ------ | ----------- | ------------------------------------------------------- |
   | `app/`                    | ✅     | ✅          | ✅                                                       |
   | `features/<x>/`           | ❌     | only `<x>`  | ✅                                                       |
   | shared layers             | ❌     | ❌          | ✅                                                       |

   Anything outside these layers (e.g. `__generated__/`, `styles/`, the Next `app/` router) is unrestricted on both sides.
3. **No routing in feature components.** Files in `features/<x>/components/` (and the feature root) must not import Next's routing modules (`next/navigation`, `next/link`, `next/router`) or any other routing library — including `Link`, `useRouter`, `usePathname`, `useParams`, `redirect`, etc. Routing is an app-level concern: the URL structure is a property of the app, not of any individual feature. When a feature component needs a CTA that navigates somewhere, accept the link as a `ReactNode` slot prop (or take an `onClick`/callback) and let the route file in `app/` supply the actual `<Link>` or navigation. Keeps features testable without router providers, embeddable in non-routed contexts (modals, Storybook, marketing pages), and free of assumptions about the app's URL shape.

   **Exception: `features/<x>/server/`.** Server Actions *may* `redirect()` — a mutation that ends in navigation (login → `/map`, logout → `/login`) is a legitimate server concern, and a route can hand a feature a navigation action to call (e.g. the upload modal calls `finishOnboarding` after a successful upload). The no-routing rule exists to keep *UI* portable; server code isn't UI, so the lint check exempts the `server/` subfolder.

If you need to share something between two features, lift it into one of the shared layers — don't import sideways. If two features genuinely depend on each other, that's a sign they're one feature.

## CSS Styling — BEM Conventions

All styles use **BEM** (Block Element Modifier) class names. No inline `style` props, no CSS-in-JS, no utility frameworks.

### Rules

- **Mobile-first**: Write base styles for small screens, then use `@media (min-width: …)` to enhance for larger viewports.
- **Design tokens** (colors, fonts, spacing, sketchy-border properties) live in `apps/web/src/styles/theme.css` as CSS custom properties on `:root`. Always use `var(--token-name)` instead of hardcoded values.
- **Component styles** live in `apps/web/src/styles/main.css`. Both files are imported from `app/layout.tsx` (`theme.css` first).
- **Block**: kebab-case matching the component's semantic role (e.g. `.health-status`).
- **Element**: double underscore (e.g. `.health-status__dot`).
- **Modifier**: double dash (e.g. `.health-status__dot--connected`).
- Organize `main.css` with `/* Block Name */` comment headers per component.
- Never use inline `style` props — use `className` with BEM classes instead.

### Reusable components: accept `className` for composition

A reusable component owns its **block** class and exposes a `className` prop so parent blocks can layer on their own BEM **element** class:

```tsx
export default function Button({ modifier = 'primary', className = '', children, ...props }) {
  const bemClass = `button button--${modifier}`;
  // Allow parent blocks to layer on their own BEM element class
  const fullClass = className ? `${bemClass} ${className}` : bemClass;

  return (
    <button className={fullClass} {...props}>
      {children}
    </button>
  );
}
```

### Parent blocks compose children via element classes

Each parent is its own BEM block. It passes its element class to children via `className`:

```tsx
// Toolbar.jsx
export default function Toolbar() {
  return (
    <div className="toolbar">
      <Button modifier="secondary">Undo</Button>
      <Button modifier="secondary">Redo</Button>
      <Button modifier="primary" className="toolbar__action">Save</Button>
    </div>
  );
}

// Dialog.jsx
export default function Dialog() {
  return (
    <div className="dialog">
      <div className="dialog__body">Are you sure?</div>
      <div className="dialog__footer">
        <Button modifier="secondary">Cancel</Button>
        <Button modifier="primary">Confirm</Button>
      </div>
    </div>
  );
}
```

## Task Tracking (GitHub Issues)

Tasks are tracked as **GitHub issues** on this repo. Use the `gh` CLI: `gh issue list`, `gh issue view <n>`, `gh issue create`, `gh issue comment`.

- Don't create, close or relabel issues autonomously: propose, then let the user decide.
- When a PR delivers an issue, put `Closes #<n>` in the PR body so the issue closes on merge.
