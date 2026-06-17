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

`account_id` and `zone_id` are non-secret identifiers, committed in
`terraform.tfvars`. Only the token is secret — supply it via the environment:

```bash
export TF_VAR_cloudflare_api_token=...     # Account: Cloudflare Tunnel edit + Zone: DNS edit
```

The public hostname isn't an input — it's derived from the zone (served at the
apex). See `local.app_hostname` in `cloudflare.tf`; to use a subdomain later,
change that local to `"app.${data.cloudflare_zone.app.name}"`.

## Cloudflare API token

Create a least-privilege custom token at
<https://dash.cloudflare.com/profile/api-tokens> → **Create Token → Custom token**,
with exactly the two permissions this config touches:

| Type    | Permission       | Access |
| ------- | ---------------- | ------ |
| Account | Cloudflare Tunnel | Edit  |
| Zone    | DNS               | Edit  |

For **Zone · DNS**, pick the plain `DNS` group (edits DNS records) — *not* DNS
Settings / DNS Firewall / DNS Views, which are unrelated products. Scope the
resources to your account and the one zone. The token is shown **once** — copy
it immediately and never commit it. Sanity-check it:

```bash
curl -s -H "Authorization: Bearer <token>" \
  https://api.cloudflare.com/client/v4/user/tokens/verify   # expect "status":"active"
```

(If you later add the WAF rulesets, extend with Account · Account Rulesets · Edit.)

### Store it in the macOS Keychain, not a dotfile

Keep the token off disk in plaintext. The empty `-w` prompts twice, hidden, so
it never lands in shell history:

```bash
security add-generic-password -a "$USER" -s cloudflare-api-token -w
```

Have Terraform read it at runtime (drop this into a gitignored direnv `.envrc`
in this dir, or a shell function — not `~/.zshrc` as a literal):

```bash
export TF_VAR_cloudflare_api_token=$(security find-generic-password -a "$USER" -s cloudflare-api-token -w)
```

Rotate by deleting and re-adding: `security delete-generic-password -s cloudflare-api-token`.

## Object storage (Tigris buckets)

`storage.tf` manages two Tigris buckets (S3-compatible, so both use the `aws`
provider pointed at the Tigris endpoint in `main.tf`, reusing the same
`AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` env credentials as the state
backend):

- **`hexagone-gpx-uploads`** — GPX uploads, with a CORS policy for the public apex
  (the browser uploads directly via backend-issued presigned PUT URLs; the prod
  analogue of `scripts/seaweedfs-init.sh`). Name must stay in sync with
  `HEXAGONE_S3_BUCKET` in `infra/k8s/base/app/backend.yaml`.
- **`hexagone-db-backups`** — Postgres logical-dump backups, with a **7-day expiry
  lifecycle rule** that enforces backup retention. Name must stay in sync with
  `BACKUP_BUCKET` in `infra/k8s/base/app/db-backup.yaml` and `scripts/prod-stack.sh`.

> If a bucket was already created by hand, import it before the first apply, e.g.:
> `terraform -chdir=infra/terraform import aws_s3_bucket.uploads hexagone-gpx-uploads`
> (and `aws_s3_bucket.db_backups hexagone-db-backups`).

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
