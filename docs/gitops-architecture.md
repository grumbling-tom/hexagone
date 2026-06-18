# GitOps / Auto-deploy Architecture

How code reaches the production k3s cluster (Mac mini, Colima): **GitHub Actions
builds, Argo CD deploys**. Pull-based, no inbound port, off the `:latest` tag.
Operational runbook lives in `infra/k8s/README.md` section 4; this file is the
*why*.

> **Status.** Target for milestone **m-1** / `TASK-0009`.
>
> | Part | Status | Where |
> |------|--------|-------|
> | Argo CD Core install + `Application` | ✅ implemented | `infra/k8s/argocd/`, `scripts/prod-stack.sh` |
> | GHCR build + SHA bump workflow | ✅ implemented | `.github/workflows/deploy.yml` |
> | Overlay pinned to GHCR SHA tags | ✅ implemented | `infra/k8s/production/kustomization.yaml` |
> | On-demand UI (`prod-stack.sh dashboard`) | ✅ implemented | `scripts/prod-stack.sh` |

## Overview

A merge to `main` deploys itself. GitHub Actions builds both images, pushes them to
GHCR tagged with the short commit SHA, and writes that SHA into the Kustomize
overlay in git. Argo CD — running in the cluster — watches `main`, sees the change,
and rolls the Deployments; k3s pulls the new SHA from GHCR. The cluster only ever
dials *outbound* (to GitHub and GHCR), so the no-inbound-port model from the
cloudflared edge is preserved end to end.

The hard split worth internalising: **Argo CD never builds images.** It reconciles
git → cluster, nothing more. Building is CI's job; the registry is the handoff.

## Decisions & rationale

**Argo CD in Core (headless) mode, not full Argo.** Core is three pods —
`application-controller`, `repo-server`, and a single-pod `redis` *cache* (no
database, no HA cluster). It drops the API/UI server, Dex (SSO), the ApplicationSet
controller, and notifications. On a 4 GiB single-node box shared with Postgres, the
app, and cloudflared, an always-on UI server pod isn't worth its footprint when one
person administers the box over Tailscale.

**On-demand UI instead of a persistent one.** The UI *is* `argocd-server`, which
Core omits — but `argocd admin dashboard` runs the API+UI as an ephemeral local
process reading the cluster from the kubeconfig (no login, no Dex). We get the full
diff/sync view when debugging and pay nothing the rest of the time. Reached over
Tailscale (SSH tunnel), never public.

**Argo CD over Flux.** Both fit the constraints; the deciding factor was the UI we
can summon on demand without hosting it. Headless Core keeps the footprint at
Flux's level. (If the UI were never wanted, Flux would be the more natural pick — it
was built headless.)

**GHCR + GitHub Actions, not build-on-box.** Argo needs the image to exist where the
cluster can pull it from the tag git references. Building on the mini would mean a
separate on-box agent still had to build *and* write the SHA to git before Argo
could sync — Argo would add three pods for the `apply` that `kubectl apply -k`
already does, and builds would tax the box. A registry makes git the single source
of truth (including the image tag), which is what makes Argo's sync/diff meaningful,
and moves builds to CI. GHCR is free for the private repo, managed, and pull-only.

**CI commits the SHA bump to git, not Argo CD Image Updater.** Image Updater would
auto-bump tags but is another in-cluster pod — against the project's
minimise-operators line. CI already runs on every merge, so it does the
`kustomize edit set image` + commit; the cluster stays at three Argo pods. The
bump commit only touches `infra/k8s/**` (and pushes use `GITHUB_TOKEN`), so it never
retriggers the build — no loop.

**SHA tags, not `:latest`.** `:latest` + `IfNotPresent` never rolls — the pod spec
doesn't change, so k3s has no reason to restart. An immutable short-SHA tag changes
the spec on every deploy, which *is* the rollout trigger, and makes rollback a
matter of pointing back at a previous SHA (or reverting the bump commit).

## The three permission grants

The private repo needs three distinct grants — none of which is Argo building
anything. Full walkthrough in `infra/k8s/README.md` section 4:

1. **Argo reads the repo** — a read-only **deploy key** (repo-server clones over SSH).
2. **CI builds + pushes images** — the Actions **`GITHUB_TOKEN`** (`packages: write`
   + `contents: write`); no manual PAT.
3. **k3s pulls images** — a **`read:packages` PAT** as the `ghcr-pull` imagePullSecret.
