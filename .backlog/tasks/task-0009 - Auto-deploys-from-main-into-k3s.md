---
id: TASK-0009
title: Auto deploys from main into k3s
status: In Progress
assignee: []
created_date: '2026-06-16 10:48'
updated_date: '2026-06-18 12:37'
labels: []
milestone: m-1
dependencies: []
ordinal: 9000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Auto-deploy code changes from `main` into the k3s cluster (Mac mini / Colima), moving off the `:latest` image tag to immutable short git SHAs.

Approach (Argo CD Core + GHCR, pull-based — preserves the no-inbound-port model):
- **Argo CD in Core (headless) mode** installed out-of-band into its own `argocd` namespace (3 pods: controller, repo-server, single-pod redis cache; no UI server, no Dex). Pull-reconciles `infra/k8s/production` from `main`.
- **GitHub Actions** (`.github/workflows/deploy.yml`) builds both images on merge to `main`, pushes them SHA-tagged to **GHCR**, and writes the SHA into the overlay via `kustomize edit set image` (committed back to `main`). Argo then syncs; k3s pulls the SHA from private GHCR.
- **On-demand UI** via `argocd admin dashboard` (`scripts/prod-stack.sh dashboard`), reached over Tailscale — no always-on server pod.
- `scripts/prod-stack.sh up` becomes bootstrap-only (installs CNPG + Argo, upserts all secrets incl. the GHCR pull secret and Argo repo deploy key, applies the Application) — it no longer builds images or `kubectl apply -k`s the app.

Plan: /Users/thomas.stokes/.claude/plans/option-1-sounds-fabulous-fuzzy-fiddle.md
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Argo CD Core installed out-of-band in the argocd namespace; only controller/repo-server/redis pods (no server/dex)
- [ ] #2 Argo CD Application reconciles infra/k8s/production from main with automated sync + selfHeal
- [ ] #3 GitHub Actions builds + pushes both images SHA-tagged to GHCR and bumps the overlay tag on merge to main (no retrigger loop)
- [ ] #4 Overlay pins images to ghcr.io/grumbling-tom/hexagone-* by SHA; :latest retired; both Deployments carry the ghcr-pull imagePullSecret
- [ ] #5 scripts/prod-stack.sh: new `dashboard` subcommand; `up` bootstraps Argo + secrets and no longer builds/applies the app
- [ ] #6 Docs updated: infra/k8s/README.md (GitOps section + UI usage + three permission grants), infra/k8s/CLAUDE.md (Argo namespacing), docs/gitops-architecture.md ADR
<!-- AC:END -->
