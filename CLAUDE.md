# Project Guidelines

## Package Manager

Use `pnpm` exclusively. Never use `npm` or `npx`.

## CSS Styling — BEM Conventions

All styles use **BEM** (Block Element Modifier) class names. No inline `style` props, no CSS-in-JS, no utility frameworks.

### Rules

- **Mobile-first**: Write base styles for small screens, then use `@media (min-width: …)` to enhance for larger viewports.
- **All styles live in** `apps/web/src/styles/main.css`, imported once from `Layout.astro`.
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
