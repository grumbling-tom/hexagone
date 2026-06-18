// Shared shape for the auth form `useActionState` state. Lives in the feature so
// the form (features) and the action (app) can both reference it without app →
// features import-rule violations (app may import from features).
//
// `sent` flags the enumeration-safe "we've accepted your request" state of the
// magic-link request form (the backend returns 202 regardless of whether the
// address is allow-listed).
export type AuthFormState = { error?: string; sent?: boolean };
