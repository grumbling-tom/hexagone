#!/usr/bin/env node
// Enforces frontend import rules. See CLAUDE.md → "Frontend Import Rules".
//
// Three rules, after bulletproof-react:
//   1. No cross-feature imports — features/X cannot import from features/Y.
//   2. Unidirectional layers — shared (components/hooks/lib/types/utils) cannot
//      import from features or app; features cannot import from app.
//   3. No routing in feature components — files under features/<x>/ may not
//      import Next's routing modules (next/navigation, next/link, next/router);
//      routing is an app-level concern (the App Router lives at apps/web/app/).
//      Exception: features/<x>/server/ (Server Actions) MAY redirect — that's a
//      legitimate server-side concern. The rule keeps *UI* embeddable/testable.

import { readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";

const SRC = resolve(import.meta.dirname, "..", "src");
const ALIAS_PREFIX = "@/";
const SHARED_LAYERS = ["components", "hooks", "lib", "types", "utils"];
const SKIP_DIRS = new Set(["__generated__", "node_modules"]);
const ROUTING_PACKAGES = ["next/navigation", "next/link", "next/router"];

function isRoutingImport(spec) {
  return ROUTING_PACKAGES.some((p) => spec === p || spec.startsWith(`${p}/`));
}

// features/<feature>/server/** holds Server Actions, which may redirect.
function isFeatureServerFile(absPath) {
  const parts = relative(SRC, absPath).split("/");
  return parts[0] === "features" && parts[2] === "server";
}

function* walk(dir) {
  for (const name of readdirSync(dir)) {
    if (SKIP_DIRS.has(name)) continue;
    const full = join(dir, name);
    if (statSync(full).isDirectory()) {
      yield* walk(full);
    } else if (/\.(ts|tsx|mts|cts)$/.test(name) && !/\.d\.ts$/.test(name)) {
      yield full;
    }
  }
}

function extractImports(source) {
  const re = /(?:from\s+|import\s*\(|import\s+)["']([^"']+)["']/g;
  return Array.from(source.matchAll(re), (m) => m[1]);
}

function resolveSpec(spec, fromFile) {
  if (spec.startsWith(ALIAS_PREFIX)) {
    return resolve(SRC, spec.slice(ALIAS_PREFIX.length));
  }
  if (spec.startsWith(".")) {
    return resolve(dirname(fromFile), spec);
  }
  return null;
}

function classify(absPath) {
  const rel = relative(SRC, absPath);
  if (rel.startsWith("..") || rel.startsWith("/")) return null;
  const [head, sub] = rel.split("/");
  if (head === "app") return { layer: "app" };
  if (head === "features") return { layer: "features", feature: sub };
  if (SHARED_LAYERS.includes(head)) return { layer: head };
  return null;
}

function violation(from, to) {
  if (
    from.layer === "features" &&
    to.layer === "features" &&
    from.feature !== to.feature
  ) {
    return `cross-feature import: features/${from.feature} → features/${to.feature}`;
  }
  if (from.layer === "features" && to.layer === "app") {
    return "features may not import from app";
  }
  if (
    SHARED_LAYERS.includes(from.layer) &&
    (to.layer === "features" || to.layer === "app")
  ) {
    return `${from.layer} may not import from ${to.layer}`;
  }
  return null;
}

const errors = [];
let scanned = 0;
for (const file of walk(SRC)) {
  scanned++;
  const fromCls = classify(file);
  if (!fromCls) continue;
  const source = readFileSync(file, "utf8");
  for (const spec of extractImports(source)) {
    if (isRoutingImport(spec)) {
      if (fromCls.layer === "features" && !isFeatureServerFile(file)) {
        errors.push(
          `${relative(SRC, file)}\n    import "${spec}" — feature components may not import routing libraries (rule 3); only features/<x>/server/ may`,
        );
      }
      continue;
    }
    const resolved = resolveSpec(spec, file);
    if (!resolved) continue;
    const toCls = classify(resolved);
    if (!toCls) continue;
    const reason = violation(fromCls, toCls);
    if (reason) {
      errors.push(`${relative(SRC, file)}\n    import "${spec}" — ${reason}`);
    }
  }
}

if (errors.length) {
  console.error("Forbidden imports:\n");
  for (const e of errors) console.error(`  ${e}\n`);
  console.error("See CLAUDE.md → Frontend Import Rules.");
  process.exit(1);
}
console.log(`Import rules OK (${scanned} files scanned)`);
