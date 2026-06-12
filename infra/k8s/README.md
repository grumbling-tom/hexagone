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

**b. Build both images.** On Colima's **docker** runtime, k3s shares the Docker
image store (via cri-dockerd), so a plain `docker build` is immediately visible
to the cluster — no registry, and no `ctr`/`nerdctl` import step. The base's
`imagePullPolicy: IfNotPresent` then uses the local image in place.
```bash
docker build -t hexagone-backend:latest apps/backend             # apps/backend/Dockerfile (ASGI, no Lambda)
docker build -t hexagone-web:latest apps/web                     # apps/web/Dockerfile (Next standalone server)

colima ssh -- sudo k3s crictl images | grep hexagone             # verify k3s sees them
```
> If you ever switch Colima to the **containerd** runtime, the build won't be
> shared — import instead with:
> `docker save hexagone-backend:latest | colima ssh -- sudo nerdctl -n k8s.io load`

**c. Create the app Secret (out of git).** Non-secret config (`ENV`, the Tigris
S3 endpoint/region/bucket) is inline in `backend.yaml`; `DATABASE_URL` comes from
CNPG's `hexagone-db-app`. The only out-of-band object is the Tigris key Secret:
```bash
kubectl create secret generic hexagone-backend-secrets \
  --from-literal=AWS_ACCESS_KEY_ID='tid_...' \
  --from-literal=AWS_SECRET_ACCESS_KEY='tsec_...'                  # Tigris keys for presigned URLs
```

**d. Apply.** Migrations run automatically — the backend Deployment has a
`migrate` init container (`alembic upgrade head`) that runs before the server.
It retries until the DB is reachable, so apply order doesn't matter:
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

## Roadmap

- **DONE — single cluster entrypoint via Next.js.** The web app is a Next.js server
  that serves the UI and reaches the backend Service server-side (RSC + Server
  Actions, via `BACKEND_ORIGIN`), so cloudflared points at one `hexagone-web` origin
  with no path rules and the browser makes no backend calls.
