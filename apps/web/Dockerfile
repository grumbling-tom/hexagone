# Web image: Next.js production server (standalone output). Serves the UI and
# reaches the backend server-side (RSC + Server Actions) at runtime via the
# BACKEND_ORIGIN env, set on the Deployment — the browser makes no backend calls,
# so there's no /api proxy and cloudflared has one entrypoint. Build context is
# apps/web:
#   docker build -t hexagone-web:latest apps/web

FROM node:22-alpine AS build
RUN npm install -g pnpm@10
WORKDIR /app

# Deps first so this layer caches unless the manifests change. pnpm 10's
# build-script gate is satisfied by pnpm.onlyBuiltDependencies in package.json
# (esbuild/sharp/biome), so the install doesn't need interactive approve-builds.
COPY package.json pnpm-lock.yaml ./
RUN --mount=type=cache,target=/pnpm/store \
    pnpm install --frozen-lockfile --store-dir=/pnpm/store

# Build the Next app -> .next (output: 'standalone'). BACKEND_ORIGIN is NOT needed
# here — it's read at runtime by the fetch client, not at build time (the static
# pages don't fetch; /map and /uploads are request-time dynamic). It's supplied as
# a runtime env on the Deployment.
COPY . .
RUN pnpm build

FROM node:22-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production \
    PORT=3000 \
    HOSTNAME=0.0.0.0

# Standalone output is a minimal server.js plus only the traced deps; static
# assets and public/ are copied alongside it.
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
COPY --from=build /app/public ./public

EXPOSE 3000
CMD ["node", "server.js"]
