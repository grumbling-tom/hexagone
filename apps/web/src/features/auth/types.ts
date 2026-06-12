// Shared shape for the auth form `useActionState` state. Lives in the feature so
// the form (features) and the action (app) can both reference it without app →
// features import-rule violations (app may import from features).
export type AuthFormState = { error?: string };
