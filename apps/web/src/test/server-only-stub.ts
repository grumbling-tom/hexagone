// `server-only` throws if imported outside a React Server Components graph. The
// test environment (happy-dom) isn't one, so vitest.config.ts aliases the
// package to this no-op, letting tests import server modules (e.g. the orval
// client / fetch mutator) and mock their behaviour.
export {};
