# `infra/terraform/` — Cloudflare edge + Tigris-backed state

Terraform root for the self-hosted stack: the **Cloudflare Tunnel** that fronts
the app, its DNS record, and (later) WAF rules. State is stored in **Tigris**.

Kept separate from the legacy AWS `terraform/` on purpose — this config manages
no AWS resources, so its Tigris backend credentials can't collide with that
config's `aws` provider.

## State backend (Tigris)

[Tigris](https://t3.storage.dev) is S3-compatible with no egress fees and
supports `If-None-Match` conditional writes, so Terraform's native `use_lockfile`
locking works without DynamoDB.

Backend blocks can't use variables, so credentials come from the environment:

```bash
export AWS_ACCESS_KEY_ID=tid_...       # Tigris access key
export AWS_SECRET_ACCESS_KEY=tsec_...  # Tigris secret
```

Bootstrap the bucket once (the backend can't create it):

```bash
aws s3 mb s3://hexagone-tfstate --endpoint-url https://t3.storage.dev
```

## Inputs

```bash
export TF_VAR_cloudflare_api_token=...     # Account: Cloudflare Tunnel edit + Zone: DNS edit
export TF_VAR_cloudflare_account_id=...
export TF_VAR_cloudflare_zone_id=...
export TF_VAR_app_hostname=app.example.com
```

## Apply

```bash
terraform -chdir=infra/terraform init
terraform -chdir=infra/terraform apply
```

## Bridge the tunnel token into the cluster

The cloudflared Deployment in `infra/k8s` needs the tunnel token. Pipe it from
the output so it never touches git:

```bash
kubectl create secret generic cloudflared-token \
  --from-literal=token="$(terraform -chdir=infra/terraform output -raw cloudflared_token)"
```

> **Open decision:** keep this manual bridge (Terraform owns the cloud, `kubectl`
> owns the cluster), or go full single-`terraform apply` by adding the
> `kbst/kustomization` provider here to apply `infra/k8s` too. Not wired — see the
> trade-offs we discussed (secrets-in-state, plan-time cluster reachability, drift
> vs. kubectl). The manual bridge is the current default.
