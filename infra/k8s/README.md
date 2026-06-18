# `infra/k8s/` — Hexagone on Colima + k3s (Mac mini)

Self-hosted deployment for the Mac mini, replicating the security pattern from
[Arcjet's "Protecting self-hosted Coolify apps"](https://blog.arcjet.com/protecting-self-hosted-coolify-apps/)
but on **k3s**, keeping operators to a minimum:

```
                    ┌──────────────────────── Mac mini ────────────────────────┐
  Internet          │  Colima VM ── k3s                                         │
     │              │   ┌──────────────┐   ┌────────────┐                       │
     │  (TLS, WAF)  │   │  cloudflared │──▶│ web (Next) │──/api──▶ backend ──▶ db │
     ▼              │   │ (Deployment) │   │ UI + proxy │                  (CNPG)│
 Cloudflare edge ◀──┼───┤  outbound    │   └────────────┘                       │
                    │   └──────────────┘   one entrypoint                       │
                    │                                                           │
                    │  tailscaled (host daemon) ── tailnet ── admin access      │
                    └───────────────────────────────────────────────────────────┘
```

- **App (public):** reachable only via **cloudflared**, which dials *outbound* to
  Cloudflare. No inbound port is ever opened. Cloudflare does TLS, DNS, WAF.
  cloudflared points at a **single origin** — the **Next.js** web Service, which
  serves the UI and reaches the backend server-side (RSC + Server Actions; the
  browser makes no backend calls), so there's no path-split and no ingress
  controller.
- **Admin (private):** **host-level `tailscaled`** puts the Mac mini on your
  tailnet. `kubectl` / dashboards are reached over the tailnet IP — never public.
- **Minimal operators.** cloudflared is a plain Deployment and Tailscale is a host
  daemon; the one operator is **CloudNativePG**, which earns it for stateful
  Postgres (failover, backups, PITR).

## Layout

```
infra/k8s/
  base/
    cloudflared/   # the public-edge tunnel
    app/           # backend + web + postgres (CNPG Cluster)
  production/       # overlay; `kubectl apply -k infra/k8s/production`
```

Tooling: **Kustomize only** (bundled in `kubectl`). No Helm.

---

## One-touch up/down — `scripts/prod-stack.sh`

For day-to-day operation, `scripts/prod-stack.sh` automates the whole runbook
below into three commands. Run it from anywhere in the repo, **on the mini**:

```bash
scripts/prod-stack.sh up              # bring the whole stack up (idempotent)
scripts/prod-stack.sh down            # delete app workloads, stop the VM (data kept)
scripts/prod-stack.sh status          # show what's running
scripts/prod-stack.sh backup          # take an on-demand Postgres dump now
scripts/prod-stack.sh restore [--yes] # restore the DB from the latest backup
scripts/prod-stack.sh dashboard       # launch the Argo CD UI on demand (over Tailscale)
```

The stack runs in a **dedicated Colima profile** (`hexagone-prod`, sized 2 CPU /
4 GiB by default — edit the vars at the top of the script), kept separate from
the `default` docker VM used by `docker compose` dev. The script pins both the
docker and kube contexts to that profile (`colima-hexagone-prod`) and starts the
VM with `--activate=false`, so it never hijacks your active context.

- **`up`** folds in the one-time bootstrap (CNPG **and Argo CD** operator installs,
  `terraform apply`) and is safe to re-run: it starts the `hexagone-prod` profile
  **with Kubernetes** if it isn't already (creating it on first run), upserts every
  Secret (app, cloudflared, the GHCR pull secret, the Argo repo deploy key), and
  applies the Argo CD `Application`, then waits on the DB cluster + all rollouts.
  It **no longer builds images or applies the overlay** — CI builds and pushes
  images to GHCR, and **Argo CD syncs the overlay from `main`** (a merge is what
  deploys). See "GitOps auto-deploy — Argo CD Core" below.
- **`down`** deletes only the stateless Deployments (`hexagone-backend`,
  `hexagone-web`, `cloudflared`) and then `colima stop`. It **deliberately leaves
  the CNPG `Cluster` (and its PVC) and the Cloudflare tunnel in place** — deleting
  the Cluster would garbage-collect the PVC and destroy the database — so `up`
  restores all data.

### Secrets live in the macOS Keychain

The script reads every secret from the login Keychain (account `$USER`), so
nothing sensitive lands on disk. Create these once on the mini (the first already
exists if you followed `infra/terraform/README.md`):

```bash
security add-generic-password -a "$USER" -s cloudflare-api-token -w           # Cloudflare API token
security add-generic-password -a "$USER" -s hexagone-tigris-access-key-id -w  # Tigris key   (tid_…)
security add-generic-password -a "$USER" -s hexagone-tigris-secret-access-key -w  # Tigris secret (tsec_…)
security add-generic-password -a "$USER" -s hexagone-resend-api-key -w        # Resend key   (re_…)
```

The Tigris keys are reused for the Terraform state backend and for
`hexagone-backend-secrets`; the Cloudflare token is `TF_VAR_cloudflare_api_token`.

### Backups & restore

Postgres is backed up by a **logical dump** (`pg_dump -Fc`), not CNPG's
continuous/PITR Barman backups — no extra operators, and each dump is a
self-contained object. A `CronJob` (`infra/k8s/base/app/db-backup.yaml`) dumps the
DB **every 6 hours** to a dedicated Tigris bucket (`hexagone-db-backups`, created
in `infra/terraform/storage.tf`); a **7-day expiry lifecycle rule** on that bucket
auto-deletes old dumps. (The rule is applied by `prod-stack.sh up` via `aws s3api`,
not Terraform — see the note in `infra/terraform/storage.tf`.) Trade-off: recovery
is to the last dump (≤6h of data loss), not point-in-time.

```bash
scripts/prod-stack.sh backup                       # fire a one-off dump now (e.g. before a risky migration)
scripts/prod-stack.sh restore [--yes]              # load the LATEST dump into the cluster (destructive)
scripts/prod-stack.sh restore --restore-from <key> # restore a SPECIFIC dump by object key
tigris ls hexagone-db-backups                      # list dumps to find a key
```

**`down` takes an off-box backup first — and aborts if it fails.** `prod-stack.sh
down` runs a backup before tearing the stack down, so data safety never depends
solely on the host PVC (the PVC is still kept for fast restarts — this just
guarantees a fresh dump in Tigris too). **A failed backup stops the teardown**; the
only way to tear down without a fresh backup is to pass `--skip-backup` explicitly.

**Recovery after a lost PVC** (new mini, `colima delete`, deleted volume — a normal
`down`/`up` keeps the PVC and needs none of this):

1. `scripts/prod-stack.sh up` — CNPG bootstraps a *fresh, empty* `hexagone` DB; the
   stack comes up healthy but with no data.
2. `scripts/prod-stack.sh restore` (or `--restore-from <key>`) — runs the on-demand
   restore Job (`infra/k8s/jobs/db-restore.yaml`, kept out of the overlay so it
   never auto-runs), which fetches the chosen dump and `pg_restore --clean`s it in,
   then restarts the backend.

Note: scheduled dumps only run while the stack is up — but `down` now takes one on
the way out, so the newest backup reflects the moment you tore the stack down.

The sections below remain the reference for what each step does (and for the
one-time Tailscale admin-plane and Colima-profile setup the script assumes).

---

## 1. Admin plane — host `tailscaled` (task #3)

Run on the **Mac mini** — the open-source daemon via Homebrew, under launchd,
**not** the GUI Tailscale.app.

> **If `Tailscale.app` is already installed on the mini, quit and remove it
> first.** The GUI app runs its own embedded `tailscaled`; it and the Homebrew
> system daemon fight over the same state and tun device. The tell: `tailscale
> status` works but there's no launchd plist at
> `/Library/LaunchDaemons/com.tailscale.tailscaled.plist`.

```bash
brew install tailscale
sudo tailscaled install-system-daemon   # launchd daemon — survives reboot, no GUI login needed
```

Authenticate. On a headless mini, prefer a **pre-auth key** (admin console →
Settings → Keys) over the interactive browser flow, and pin a stable hostname so
the box is identifiable on the tailnet:

```bash
sudo tailscale up \
  --hostname=hexagone-mini \
  --auth-key=tskey-auth-...   # omit to fall back to the interactive browser login

tailscale ip -4              # the mini's tailnet IP
```

Then, in the admin console, **disable key expiry** for `hexagone-mini` — a server
shouldn't silently drop off the tailnet when its node key expires.

**Verify it's a real system daemon (survives reboot), not just a live process:**

```bash
sudo launchctl print system/com.tailscale.tailscaled | grep -E "state|pid"
tailscale status            # self shows as hexagone-mini, no "offline"
```

> `--ssh` (Tailscale SSH server) is Linux-only. On macOS, enable **System
> Settings → General → Sharing → Remote Login** and SSH to the mini over its
> tailnet IP instead.

**Reaching the cluster remotely (from your laptop, also on the tailnet):**
- Simplest: `ssh <mini-tailnet-ip>` and run `kubectl` locally on the mini
  (Colima already wrote its kubeconfig there).
- Or copy the kubeconfig and repoint its `server:` at the mini's tailnet IP
  (advanced — requires exposing the k3s API on that interface).

Nothing here is public.

## 2. App edge — cloudflared (task #4)

The tunnel, its DNS record, and routing are managed by Terraform
(`infra/terraform/`): cloudflared dials outbound to a single origin — the Next.js
web Service, which serves the UI and proxies `/api` to the backend. Cloudflare
manages DNS + TLS; add WAF / rate-limit rules in `infra/terraform/cloudflare.tf`.

After `terraform apply`, bridge the run token into the cluster (never in git):

```bash
kubectl create secret generic cloudflared-token \
  --from-literal=token="$(terraform -chdir=infra/terraform output -raw cloudflared_token)"
```

## 3. App workloads (task #2)

Decided: Postgres via **CloudNativePG** in-cluster, and the **web app served from
the cluster** (Next.js server that also proxies `/api`) — S3/CloudFront for the SPA
is retired. Four prerequisites before `apply`:

**a. Install the CNPG operator (one-time, cluster-wide).** Not in the overlay —
the `namespace: default` transformer would rewrite the operator's own namespace.
```bash
kubectl apply --server-side -f \
  https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/release-1.29/releases/cnpg-1.29.0.yaml
kubectl -n cnpg-system rollout status deploy/cnpg-controller-manager
```
(confirm the exact patch tag at github.com/cloudnative-pg/cloudnative-pg/releases)

**b. Images — built by CI now.** Production images come from **GHCR**, built and
pushed by GitHub Actions on merge to `main` (see section 4 "GitOps auto-deploy");
the cluster pulls them with the `ghcr-pull` secret. The local build below is only
the **escape hatch** for an unmerged image. On Colima's **docker** runtime, k3s
shares the Docker image store (via cri-dockerd), so a plain `docker build` is
immediately visible to the cluster — no registry, and no `ctr`/`nerdctl` import
step. The base's `imagePullPolicy: IfNotPresent` then uses the local image in place.
```bash
docker build -t hexagone-backend:latest apps/backend             # apps/backend/Dockerfile (ASGI, no Lambda)
docker build -t hexagone-web:latest apps/web                     # apps/web/Dockerfile (Next standalone server)

colima ssh -- sudo k3s crictl images | grep hexagone             # verify k3s sees them
```
> If you ever switch Colima to the **containerd** runtime, the build won't be
> shared — import instead with:
> `docker save hexagone-backend:latest | colima ssh -- sudo nerdctl -n k8s.io load`

**c. Create the app Secret (out of git).** Non-secret config (`ENV`, the Tigris
S3 endpoint/region/bucket, `RESEND_FROM_EMAIL`) is inline in `backend.yaml`;
`DATABASE_URL` comes from CNPG's `hexagone-db-app`. The out-of-band object is the
app Secret, holding the Tigris keys and the Resend API key:
```bash
kubectl create secret generic hexagone-backend-secrets \
  --from-literal=AWS_ACCESS_KEY_ID='tid_...' \
  --from-literal=AWS_SECRET_ACCESS_KEY='tsec_...' \               # Tigris keys for presigned URLs
  --from-literal=RESEND_API_KEY='re_...'                          # Resend key for transactional email
```

**d. Apply — Argo's job now.** `scripts/prod-stack.sh up` applies the Argo
`Application` and **Argo CD syncs the overlay** (section 4 "GitOps auto-deploy");
the raw `kubectl apply -k` below is the underlying equivalent for a manual bring-up.
Migrations run automatically either way — the backend Deployment has a `migrate`
init container (`alembic upgrade head`) that runs before the server. It retries
until the DB is reachable, so apply order doesn't matter:
```bash
kubectl apply -k infra/k8s/production
kubectl wait --for=condition=Ready cluster/hexagone-db --timeout=300s   # CNPG ready
kubectl rollout status deploy/hexagone-backend                         # waits past migrate init
```

## Apply & verify

```bash
kubectl kustomize infra/k8s/production      # render & eyeball first
kubectl apply -k infra/k8s/production

kubectl get pods                                       # all Running
kubectl get cluster hexagone-db                        # CNPG: instances ready, no errors
kubectl logs deploy/cloudflared | grep -i registered   # tunnel connected to edge
curl -I https://<your-apex>                            # 200 from server: cloudflare
curl -s https://<your-apex>/api/health                 # backend healthy through the tunnel
```

## Pre-flight checks (one-time)

```bash
kubectl get nodes                  # one Ready node
kubectl get storageclass           # local-path is (default) — for the postgres PVC
kubectl get pods -n kube-system    # what Colima's k3s actually enabled
```

## 4. GitOps auto-deploy — Argo CD Core (task #9)

Merges to `main` deploy themselves. **Argo CD** (in **Core** mode — headless) runs
in-cluster and pull-reconciles the production overlay from git; **GitHub Actions**
builds the images. Argo CD **never builds images** — it only reconciles git →
cluster — so building is CI's job and the cluster only ever *pulls*.

```
  merge → main
      │  GitHub Actions (.github/workflows/deploy.yml)
      ├─ build 2 images ──push :<sha>──▶ GHCR (ghcr.io/grumbling-tom/hexagone-*)
      └─ kustomize set image :<sha> ──commit──▶ main (infra/k8s/production)
                                            │
   ┌──────────── Mac mini / k3s ───────────┼───────────────┐
   │  Argo CD Core (ns: argocd) ◀─watch main┘               │
   │    repo-server (clone via read-only deploy key)        │
   │    application-controller ──apply──▶ default ns        │
   │        backend / web pods ──pull :<sha>──▶ GHCR        │
   └────────────────────────────────────────────────────────┘
```

**Why Core (headless):** three pods — `application-controller`, `repo-server`, a
single-pod `redis` *cache* (no database) — and **no** always-on API/UI server,
Dex, ApplicationSet or notifications controllers. The UI is launched **on demand**
(below), so we get the diff/sync view when debugging without an idle server pod on
the 4 GiB box. This finally retires the `:latest` tag: each deploy pins an
**immutable short-SHA** tag, and that change to the pod spec is what triggers the
rollout.

### Install (one-time, out-of-band)

Like the CNPG operator, Argo is a controller: it lives in its **own** `argocd`
namespace and is **not** part of the overlay (`infra/k8s/CLAUDE.md`).
`scripts/prod-stack.sh up` does this for you; the manual equivalent is:

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f \
  https://raw.githubusercontent.com/argoproj/argo-cd/v2.13.3/manifests/core-install.yaml
# confirm/bump the latest stable tag at github.com/argoproj/argo-cd/releases — pin it
kubectl -n argocd rollout status deploy/argocd-repo-server
```

The one app-level CR — the `Application` that points Argo at the overlay — lives in
`infra/k8s/argocd/application.yaml` (kept out of the overlay it manages, which would
otherwise be circular) and is applied out-of-band by `up`.

### The three permission grants

The repo is **private**, so three *distinct* grants are needed — none of which is
"let Argo build images" (that capability doesn't exist). Each secret is read from
the macOS Keychain by `prod-stack.sh`, same as the others.

**1. Argo reads the repo — a read-only deploy key.** Minimal scope: one repo,
read-only.

```bash
ssh-keygen -t ed25519 -C "argocd-hexagone" -f /tmp/argocd_deploy -N ""
# • Public key  → GitHub repo → Settings → Deploy keys → "Add deploy key"
#                 (leave "Allow write access" UNCHECKED)
# • Private key → Keychain (prod-stack.sh builds the Argo `repository` Secret from it)
security add-generic-password -a "$USER" -s hexagone-argocd-deploy-key -w "$(cat /tmp/argocd_deploy)"
rm /tmp/argocd_deploy /tmp/argocd_deploy.pub
```

**2. CI builds + pushes images — the Actions `GITHUB_TOKEN`, no manual PAT.** The
workflow's built-in token pushes to GHCR under the same owner and commits the tag
bump (`permissions: { contents: write, packages: write }`). One-time after the first
push: GitHub → your profile → **Packages** → `hexagone-backend` / `hexagone-web` →
**Package settings** → link to the repo (keeps the package private; Actions still
pushes).

**3. k3s pulls from private GHCR — a read-only PAT.** The cluster is an *external*
puller (not Actions), so it needs its own token. Create a **classic PAT with only
`read:packages`**:

```bash
# GitHub → Settings → Developer settings → Personal access tokens (classic)
#        → scope: read:packages
security add-generic-password -a "$USER" -s hexagone-ghcr-pull-token -w   # paste the PAT
```

`prod-stack.sh up` turns this into the `ghcr-pull` `dockerconfigjson` Secret in
`default`; both Deployments reference it via `imagePullSecrets`.

### Using the UI (on demand)

Core mode has no UI server pod — `argocd admin dashboard` runs the API+UI as a
local process that reads the cluster straight from the kubeconfig (no login, no
Dex). Run it **on the mini**:

```bash
scripts/prod-stack.sh dashboard          # serves the UI on 127.0.0.1:8080
```

The script pins the prod kube context for you (via a throwaway kubeconfig — your
active `kubectl` context is left untouched) and binds to `127.0.0.1`. From your
laptop (also on the tailnet), tunnel to it over SSH and open the URL — nothing is
ever exposed publicly, consistent with the rest of the admin plane:

```bash
ssh -L 8080:127.0.0.1:8080 <hexagone-mini-tailnet-ip>   # then browse http://127.0.0.1:8080
```

Quit it (Ctrl-C) and the cluster is back to the three headless Argo pods. CLI
equivalents (also Core, no server): `argocd app get hexagone --core`,
`argocd app sync hexagone --core`, `argocd app rollback hexagone --core`.

### Day-to-day & rollback

- **Deploy:** merge to `main`. CI builds + pushes + bumps the SHA; Argo rolls the
  cluster. Watch it in the dashboard or `kubectl -n argocd get application hexagone`.
- **Rollback:** `argocd app rollback hexagone --core` (or revert the bump commit on
  `main` — git is the source of truth, so Argo follows).

### Escape hatch — emergency local image

The happy path is "merge to main". To force an unmerged build onto the cluster
without CI (e.g. testing a hotfix), build straight into the prod profile's docker
store and point the Deployment at it by digest/tag — this bypasses Argo, which will
`selfHeal` it back to git on its next sync, so treat it as temporary:

```bash
docker --context colima-hexagone-prod build -t hexagone-backend:hotfix apps/backend
kubectl --context colima-hexagone-prod set image deploy/hexagone-backend backend=hexagone-backend:hotfix
```

(On Colima's **docker** runtime k3s shares the image store, so the local tag is
visible with no registry. On the **containerd** runtime, import it first with the
`nerdctl load` step from section 3, step b.)

## Roadmap

- **DONE — single cluster entrypoint via Next.js.** The web app is a Next.js server
  that serves the UI and reaches the backend Service server-side (RSC + Server
  Actions, via `BACKEND_ORIGIN`), so cloudflared points at one `hexagone-web` origin
  with no path rules and the browser makes no backend calls.
- **DONE — GitOps auto-deploy (task #9).** Argo CD Core pull-reconciles the overlay
  from `main`; GitHub Actions builds + pushes SHA-tagged images to GHCR and bumps the
  overlay. A merge deploys; the `:latest` tag is retired. See section 4.
