# Project Guidelines

## Package Manager

Use `pnpm` exclusively. Never use `npm` or `npx`.

## Frontend File Organisation

Code under `apps/web/src/` is grouped by **feature**, not by file type. New components default to a feature folder; only promote to top-level `components/` once something is genuinely reused across features.

```
apps/web/src/
  app/                  App shell: routing, providers, page chrome
    App.tsx             Root <BrowserRouter> + <QueryClientProvider>
    Nav.tsx             Top nav
    ProtectedRoute.tsx  Auth guard
    pages/              Route components — kept thin, compose feature components
  features/             One folder per domain feature
    uploads/
      UploadList.tsx
      UploadForm.tsx
      ...
    map/                (added when MapView lands)
  components/           Truly shared, generic primitives (e.g. Button) — empty until needed
  lib/                  Cross-cutting non-React utilities (fetch client, etc.)
  styles/               theme.css + main.css (see CSS section below)
  __generated__/        Orval-generated API client — do not edit by hand
```

The **Next.js App Router** lives at `apps/web/app/` (project root, *outside* `src/`): thin route files that own the HTML shell, the landing page, and a client catch-all that mounts the `src/app/` SPA. Everything under `src/` stays organised by feature as above.

**Where to put a new file**:
- Used by exactly one feature → `features/<feature>/`
- Part of the app chrome or routing → `app/`
- Reused across two or more features → `components/`
- Non-React utility → `lib/`

**Imports**: always use the `@/` alias (mapped to `src/`). Do not use deep relative paths like `../../features/uploads/UploadList`.

### Frontend Import Rules

Adapted from [bulletproof-react](https://github.com/alan2207/bulletproof-react/blob/master/docs/project-structure.md). Enforced by `pnpm lint:imports` (script at `apps/web/scripts/check-imports.mjs`, runs on pre-commit via lefthook).

Three rules:

1. **No cross-feature imports.** A file in `features/uploads/` may not import from `features/map/`. Compose features at the page/app layer instead.
2. **Unidirectional layers.** Code flows `shared → features → app`, never the other way:

   | From ↓ \ To →             | `app/` | `features/` | shared (`components`, `hooks`, `lib`, `types`, `utils`) |
   | ------------------------- | ------ | ----------- | ------------------------------------------------------- |
   | `app/`                    | ✅     | ✅          | ✅                                                       |
   | `features/<x>/`           | ❌     | only `<x>`  | ✅                                                       |
   | shared layers             | ❌     | ❌          | ✅                                                       |

   Anything outside these layers (e.g. `__generated__/`, `styles/`, the Next `app/` router) is unrestricted on both sides.
3. **No routing in features.** Files in `features/` must not import from `react-router-dom` (or any other routing library) — including `Link`, `useNavigate`, `useLocation`, `useParams`, `Outlet`, etc. Routing is an app-level concern: the URL structure is a property of the app, not of any individual feature. When a feature component needs a CTA that navigates somewhere, accept the link as a `ReactNode` slot prop (or take an `onClick` callback) and let the parent in `app/pages/` supply the actual `<Link>`. Keeps features testable without `<MemoryRouter>` providers, embeddable in non-routed contexts (modals, Storybook, marketing pages), and free of assumptions about the app's URL shape.

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
