# Web image: Next.js production server (standalone output). Serves the UI AND
# proxies /api to the backend (next.config.mjs rewrites), so cloudflared no longer
# path-splits — one entrypoint into the cluster. Build context is apps/web:
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

# The /api proxy target is baked at build time — Next evaluates next.config
# rewrites() during `next build`, not at runtime. Defaults to the in-cluster
# backend Service; override for other environments with --build-arg.
ARG BACKEND_ORIGIN=http://hexagone-backend.default.svc.cluster.local:8000
ENV BACKEND_ORIGIN=$BACKEND_ORIGIN

# Build the Next app -> .next (output: 'standalone').
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
