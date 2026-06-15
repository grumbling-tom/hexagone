#!/usr/bin/env node
// Enforces that the Next.js App Router directory (apps/web/app/) stays routing
// only. Route files compose pages from feature components and Server Actions;
// Server Actions themselves live in features/<x>/server/ and are imported by the
// route. So no `actions.ts` is allowed under app/. See CLAUDE.md → "Frontend
// File Organisation".

import { readdirSync, statSync } from "node:fs";
import { basename, join, relative, resolve } from "node:path";

const ROOT = resolve(import.meta.dirname, "..");
const APP = resolve(ROOT, "app");
const FORBIDDEN_BASENAMES = new Set(["actions.ts", "actions.tsx"]);

function* walk(dir) {
  for (const name of readdirSync(dir)) {
    const full = join(dir, name);
    if (statSync(full).isDirectory()) {
      yield* walk(full);
    } else {
      yield full;
    }
  }
}

const offenders = [];
for (const file of walk(APP)) {
  if (FORBIDDEN_BASENAMES.has(basename(file))) {
    offenders.push(relative(ROOT, file));
  }
}

if (offenders.length) {
  console.error("Server Actions are not allowed under app/ (routing only):\n");
  for (const f of offenders) console.error(`  ${f}`);
  console.error(
    "\nMove them to features/<feature>/server/ and import them from the route.\n" +
      "See CLAUDE.md → Frontend File Organisation.",
  );
  process.exit(1);
}

console.log("app/ structure OK (no Server Action files under app/)");
