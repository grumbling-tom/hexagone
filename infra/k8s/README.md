# `infra/k8s/` — Hexagone on Colima + k3s (Mac mini)

Self-hosted deployment for the Mac mini, replicating the security pattern from
[Arcjet's "Protecting self-hosted Coolify apps"](https://blog.arcjet.com/protecting-self-hosted-coolify-apps/)
but on **k3s** with **zero operators**:

```
                    ┌─────────────────────── Mac mini ───────────────────────┐
  Internet          │  Colima VM ── k3s ──────────────────────────────────┐  │
     │              │   ┌──────────────┐   ┌──────────────┐   ┌─────────┐  │  │
     │  (TLS, WAF)  │   │  cloudflared │──▶│   Traefik    │──▶│ backend │  │  │
     ▼              │   │ (Deployment) │   │  (Ingress)   │   │ postgres│  │  │
 Cloudflare edge ◀──┼───┤  outbound    │   └──────────────┘   └─────────┘  │  │
                    │   └──────────────┘                                   │  │
                    │  tailscaled (host daemon) ── tailnet ── admin access ┘  │
                    └─────────────────────────────────────────────────────────┘
```

- **App (public):** reachable only via **cloudflared**, which dials *outbound* to
  Cloudflare. No inbound port is ever opened. Cloudflare does TLS, DNS, WAF.
- **Admin (private):** **host-level `tailscaled`** puts the Mac mini on your
  tailnet. `kubectl` / dashboards are reached over the tailnet IP — never public.
- **No operators, no CRDs.** cloudflared is a plain Deployment; Tailscale is a
  host daemon.

## Layout

```
infra/k8s/
  base/
    cloudflared/   # the public-edge tunnel (complete)
    app/           # backend + postgres + ingress  (SKELETON — task #2)
  production/       # overlay; `kubectl apply -k infra/k8s/production`
```

Tooling: **Kustomize only** (bundled in `kubectl`). No Helm.

---

## 1. Admin plane — host `tailscaled` (task #3)

Run on the **Mac mini** (the open-source daemon via Homebrew, not the GUI app):

```bash
brew install tailscale
sudo tailscaled install-system-daemon      # runs tailscaled under launchd
sudo tailscale up                          # authenticate in the browser
tailscale ip -4                            # the mini's tailnet IP
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

1. **Cloudflare dashboard:** Zero Trust → Networks → Tunnels → **Create tunnel**
   (type *Cloudflared*). Copy the **tunnel token** (`eyJ...`).
2. **Store the token** as a Secret (kept out of git):
   ```bash
   kubectl create secret generic cloudflared-token \
     --from-literal=token='eyJ...'
   ```
3. **Public hostname:** in the tunnel's *Public Hostnames* tab, map your hostname
   (e.g. `app.example.com`) to the in-cluster Traefik:
   ```
   Service:  http://traefik.kube-system.svc.cluster.local:80
   ```
   Cloudflare manages DNS + TLS for that hostname. Add WAF / rate-limit rules here.

## 3. App workloads (task #2 — SKELETON, not yet wired)

Before applying, resolve the TODOs flagged in `base/app/`:
- **Backend image** — build a server image (Dockerfile.lambda `dev` target runs
  uvicorn today) and set it in `production/kustomization.yaml` `images:`.
- **Postgres vs RDS** — keep `postgres.yaml` (in-cluster, local disk) or delete it
  and point `DATABASE_URL` at RDS over the tailnet.
- **Frontend A/B** — A: serve the SPA from the cluster (uncomment the `/` route in
  `ingress.yaml` + add a `hexagone-web` Deployment) and retire S3/CloudFront; or
  B: keep the SPA on S3/CloudFront and tunnel only `/api`.

Secrets/config to create (out of git):
```bash
kubectl create secret generic postgres-secrets \
  --from-literal=POSTGRES_USER=postgres \
  --from-literal=POSTGRES_PASSWORD='...' \
  --from-literal=POSTGRES_DB=postgres

kubectl create configmap hexagone-backend-config \
  --from-literal=ENV=PROD \
  --from-literal=DATABASE_URL='postgresql://postgres:...@postgres:5432/postgres'

kubectl create secret generic hexagone-backend-secrets \
  --from-literal=AWS_ACCESS_KEY_ID='...' \
  --from-literal=AWS_SECRET_ACCESS_KEY='...'
```

## Apply

```bash
kubectl kustomize infra/k8s/production      # render & eyeball first
kubectl apply -k infra/k8s/production
```

## Verify

```bash
kubectl get pods                                   # cloudflared Running; app pods once wired
kubectl logs deploy/cloudflared | grep -i registered   # tunnel connected to edge
kubectl get pods -n kube-system | grep traefik     # confirm Traefik is present
```

## Pre-flight checks (one-time)

```bash
kubectl get nodes                  # one Ready node
kubectl get storageclass           # local-path is (default) — for the postgres PVC
kubectl get pods -n kube-system    # what Colima's k3s actually enabled
```

## Roadmap

- **TODO — migrate the frontend to Next.js for a single cluster entrypoint.**
  Today the architecture assumes a separate Astro SPA (on S3/CloudFront, or an
  in-cluster nginx) alongside the FastAPI backend, which is why cloudflared
  forwards to **Traefik** and an `Ingress` splits `/api` from `/`. Moving the web
  app to **Next.js** would let one server own both the UI and routing (Next.js
  `rewrites` proxy `/api/*` to the backend Service). cloudflared could then point
  at a single `hexagone-web` Service and we could **retire Traefik + the Ingress
  path-split** entirely — one front door into the cluster.
