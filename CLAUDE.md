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
  pages/                Astro entry points (`index.astro`, `app.astro`) — not React routes
```

**Where to put a new file**:
- Used by exactly one feature → `features/<feature>/`
- Part of the app chrome or routing → `app/`
- Reused across two or more features → `components/`
- Non-React utility → `lib/`

**Imports**: always use the `@/` alias (mapped to `src/`). Do not use deep relative paths like `../../features/uploads/UploadList`.

## CSS Styling — BEM Conventions

All styles use **BEM** (Block Element Modifier) class names. No inline `style` props, no CSS-in-JS, no utility frameworks.

### Rules

- **Mobile-first**: Write base styles for small screens, then use `@media (min-width: …)` to enhance for larger viewports.
- **Design tokens** (colors, fonts, spacing, sketchy-border properties) live in `apps/web/src/styles/theme.css` as CSS custom properties on `:root`. Always use `var(--token-name)` instead of hardcoded values.
- **Component styles** live in `apps/web/src/styles/main.css`. Both files are imported from `Layout.astro` (`theme.css` first).
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
