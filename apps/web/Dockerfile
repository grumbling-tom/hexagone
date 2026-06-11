# Web image: build the Astro static site (apps/web) and serve it with nginx.
#
# Self-contained: the generated API client is committed, and the app calls /api
# same-origin (PUBLIC_BACKEND_BASE_URL unset => relative URLs), so neither the
# backend nor a build-time API URL is needed. Build context is apps/web:
#   docker build -t hexagone-web:latest apps/web
#
# nginx's default.conf is replaced at runtime by the SPA-fallback config from the
# hexagone-web-nginx ConfigMap (infra/k8s/base/app/frontend.yaml); this image
# ships only the static assets.

FROM node:22-alpine AS build
# Pin pnpm 9 (matches the v9 lockfile). pnpm 10 gates dependency build scripts
# (esbuild, sharp) behind interactive `approve-builds` and fails a CI install;
# pnpm 9 runs them automatically.
RUN npm install -g pnpm@9
WORKDIR /app

# Install deps first so this layer caches unless the manifests change.
COPY package.json pnpm-lock.yaml ./
RUN --mount=type=cache,target=/pnpm/store \
    pnpm install --frozen-lockfile --store-dir=/pnpm/store

# Build the static site -> dist/ (astro build; output defaults to "static").
COPY . .
RUN pnpm build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
