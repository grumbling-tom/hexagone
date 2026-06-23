#!/usr/bin/env bash
#
# prod-stack.sh — spin the Hexagone production stack up and down on the Mac mini
# (Colima VM -> k3s). One command replaces the manual runbook in
# infra/k8s/README.md + infra/terraform/README.md.
#
# Usage:
#   scripts/prod-stack.sh up                         bring the whole stack up (idempotent)
#   scripts/prod-stack.sh down [--skip-backup]       back up the DB, then stop the VM
#   scripts/prod-stack.sh status                     show what's running
#   scripts/prod-stack.sh backup                     take an on-demand Postgres dump now
#   scripts/prod-stack.sh restore [--yes] [--restore-from <key>]
#                                                    restore the DB (latest, or a specific dump)
#   scripts/prod-stack.sh dashboard [port]           launch the Argo CD UI (on-demand)
#
# `up` folds in the one-time bootstrap (CNPG + Argo CD operators, Cloudflare
# tunnel, all out-of-band Secrets) and is safe to re-run. It does NOT build images
# or apply the app overlay any more: CI builds and pushes images to GHCR, and Argo
# CD syncs the overlay from main — a merge to main is what deploys. `down`
# deliberately leaves the CNPG database Cluster (and its PVC) and the Cloudflare
# tunnel in place, so `up` restores all data.
#
# The stack runs in a DEDICATED Colima profile (COLIMA_PROFILE below), separate
# from the `default` docker VM used by docker-compose dev. Colima names that
# profile's docker + kube contexts `colima-<profile>`; the script pins both
# explicitly (via the `k` and `dkr` wrappers) and starts the VM with
# --activate=false so it never hijacks your active docker/kube context.

set -euo pipefail

# --- Config -----------------------------------------------------------------

# Dedicated Colima profile + VM sizing for the prod stack. Edit to taste; the
# Mac mini's total RAM is the ceiling on COLIMA_MEMORY.
COLIMA_PROFILE="hexagone-prod"
COLIMA_CPU=2
COLIMA_MEMORY=4      # GiB
COLIMA_DISK=60       # GiB

# Colima derives these context names from the profile (default profile -> just
# `colima`; named profile `x` -> `colima-x`).
KUBE_CONTEXT="colima-${COLIMA_PROFILE}"
DOCKER_CONTEXT="colima-${COLIMA_PROFILE}"

# CloudNativePG operator release (installed out-of-band, never in the overlay —
# see infra/k8s/CLAUDE.md). Bump alongside the version in infra/k8s/README.md.
CNPG_VERSION="1.29.0"
CNPG_BRANCH="release-1.29"
CNPG_MANIFEST="https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/${CNPG_BRANCH}/releases/cnpg-${CNPG_VERSION}.yaml"

# Argo CD in Core mode — headless: controller + repo-server + a single-pod redis
# cache, no UI server, no Dex (the UI is launched on demand, see `dashboard`).
# Installed out-of-band into its own `argocd` namespace, like CNPG. Confirm/bump
# the latest stable tag at github.com/argoproj/argo-cd/releases.
ARGOCD_VERSION="v2.13.3"
ARGOCD_MANIFEST="https://raw.githubusercontent.com/argoproj/argo-cd/${ARGOCD_VERSION}/manifests/core-install.yaml"
ARGOCD_APP_MANIFEST="infra/k8s/argocd/application.yaml"

# Private GHCR access. k3s pulls the SHA-tagged images using a read:packages PAT
# (Keychain: hexagone-ghcr-pull-token) wired in as the `ghcr-pull` Secret; Argo's
# repo-server clones the repo over SSH with a read-only deploy key (Keychain:
# hexagone-argocd-deploy-key). See infra/k8s/README.md, "GitOps auto-deploy".
GHCR_USER="grumbling-tom"
GHCR_PULL_SECRET="ghcr-pull"
REPO_SSH_URL="git@github.com:grumbling-tom/hexagone.git"

TIGRIS_ENDPOINT="https://t3.storage.dev"
TF_STATE_BUCKET="hexagone-tfstate"
TF_DIR="infra/terraform"

# Postgres backups: dedicated Tigris bucket (created in infra/terraform/storage.tf
# with a 7-day expiry rule) + the on-demand restore Job (kept out of the overlay).
BACKUP_BUCKET="hexagone-db-backups"
RESTORE_MANIFEST="infra/k8s/jobs/db-restore.yaml"

# GPX uploads bucket (created in infra/terraform/storage.tf). The Tigris object
# notification on this bucket POSTs to the backend's upload-processing-jobs
# webhook; objects land under the v1/uploads/ prefix.
UPLOADS_BUCKET="hexagone-gpx-uploads"

# Stateless deployments `down` tears down. The CNPG Cluster (hexagone-db) is
# excluded on purpose: deleting it garbage-collects its PVC and destroys the DB.
STATELESS_DEPLOYMENTS=(hexagone-backend hexagone-web cloudflared)

# --- Helpers ----------------------------------------------------------------

log()  { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33mwarn:\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31merror:\033[0m %s\n' "$*" >&2; exit 1; }

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "missing required command: $1"
}

# kubectl / docker pinned to the prod profile's contexts, so the script never
# depends on (or disturbs) your currently-active context.
k()   { kubectl --context "$KUBE_CONTEXT" "$@"; }
dkr() { docker --context "$DOCKER_CONTEXT" "$@"; }

# Read a secret from the macOS login Keychain (account = $USER), matching the
# convention in infra/terraform/README.md.
kc() {
  security find-generic-password -a "$USER" -s "$1" -w 2>/dev/null \
    || die "missing Keychain entry '$1'. Add it with:
    security add-generic-password -a \"\$USER\" -s $1 -w"
}

# Is the prod Colima profile up AND running (VM state, not k8s)?
profile_running() {
  colima status "$COLIMA_PROFILE" 2>&1 | grep -qi running
}

# Ensure the prod profile is running with Kubernetes reachable. Handles all three
# states: not created, running-without-k8s, and already-good.
ensure_vm() {
  if profile_running && k get --raw /healthz >/dev/null 2>&1; then
    log "Colima profile '$COLIMA_PROFILE' running with Kubernetes"
    return
  fi
  if profile_running; then
    log "Profile '$COLIMA_PROFILE' running but Kubernetes not reachable — enabling"
  else
    log "Starting Colima profile '$COLIMA_PROFILE' (${COLIMA_CPU} CPU / ${COLIMA_MEMORY} GiB)"
  fi
  colima start "$COLIMA_PROFILE" \
    --kubernetes \
    --cpu "$COLIMA_CPU" --memory "$COLIMA_MEMORY" --disk "$COLIMA_DISK" \
    --activate=false
}

# --- up ---------------------------------------------------------------------

cmd_up() {
  for arg in "$@"; do
    case "$arg" in
      # No --build any more: CI builds and pushes images to GHCR. For an emergency
      # local image override, see the "escape hatch" note in infra/k8s/README.md.
      *) die "unknown option for up: $arg (up takes none — CI builds images, Argo deploys)" ;;
    esac
  done

  # 1. Preflight ------------------------------------------------------------
  log "Preflight: checking tools and Keychain entries"
  for c in colima kubectl docker terraform aws security tigris; do need_cmd "$c"; done
  # Verify every Keychain entry up front so we fail fast, not mid-apply.
  local cf_token tigris_id tigris_secret resend_key ghcr_pull_token argocd_deploy_key upload_notification_secret
  cf_token="$(kc cloudflare-api-token)"
  tigris_id="$(kc hexagone-tigris-access-key-id)"
  tigris_secret="$(kc hexagone-tigris-secret-access-key)"
  resend_key="$(kc hexagone-resend-api-key)"
  ghcr_pull_token="$(kc hexagone-ghcr-pull-token)"     # read:packages PAT — k3s pulls from GHCR
  argocd_deploy_key="$(kc hexagone-argocd-deploy-key)" # read-only deploy key — Argo clones the repo
  # Shared secret for the upload-processing-jobs webhook. The SAME value seeds the
  # backend Secret (so it validates the Bearer token) and the Tigris notification
  # --token below, so the two can never drift.
  upload_notification_secret="$(kc hexagone-upload-notification-secret)"

  # 2. Colima + k3s ---------------------------------------------------------
  ensure_vm
  log "Waiting for the k3s node to be Ready"
  k wait --for=condition=Ready nodes --all --timeout=120s

  # 3. Tigris state bucket (one-time, guarded) ------------------------------
  if AWS_ACCESS_KEY_ID="$tigris_id" AWS_SECRET_ACCESS_KEY="$tigris_secret" \
       aws s3 ls "s3://${TF_STATE_BUCKET}" --endpoint-url "$TIGRIS_ENDPOINT" >/dev/null 2>&1; then
    log "Terraform state bucket present"
  else
    log "Creating Terraform state bucket s3://${TF_STATE_BUCKET}"
    AWS_ACCESS_KEY_ID="$tigris_id" AWS_SECRET_ACCESS_KEY="$tigris_secret" \
      aws s3 mb "s3://${TF_STATE_BUCKET}" --endpoint-url "$TIGRIS_ENDPOINT"
  fi

  # 4. Operators (idempotent) — CNPG + Argo CD Core. Both installed out-of-band,
  # each in its own namespace (infra/k8s/CLAUDE.md), and both must exist before
  # the Argo Application syncs the overlay: CNPG owns the Cluster CR, Argo owns
  # the app rollout.
  if k get deploy cnpg-controller-manager -n cnpg-system >/dev/null 2>&1; then
    log "CNPG operator already installed"
  else
    log "Installing CNPG operator ${CNPG_VERSION}"
    k apply --server-side -f "$CNPG_MANIFEST"
    k -n cnpg-system rollout status deploy/cnpg-controller-manager --timeout=180s
  fi

  if k get deploy argocd-repo-server -n argocd >/dev/null 2>&1; then
    log "Argo CD (Core) already installed"
  else
    log "Installing Argo CD (Core) ${ARGOCD_VERSION}"
    k create namespace argocd --dry-run=client -o yaml | k apply -f -
    k -n argocd apply -f "$ARGOCD_MANIFEST"
    k -n argocd rollout status deploy/argocd-repo-server --timeout=180s
  fi

  # 5. Terraform (idempotent apply) -----------------------------------------
  log "Applying Cloudflare tunnel via Terraform"
  AWS_ACCESS_KEY_ID="$tigris_id" AWS_SECRET_ACCESS_KEY="$tigris_secret" \
  TF_VAR_cloudflare_api_token="$cf_token" \
    terraform -chdir="$TF_DIR" init -input=false >/dev/null
  AWS_ACCESS_KEY_ID="$tigris_id" AWS_SECRET_ACCESS_KEY="$tigris_secret" \
  TF_VAR_cloudflare_api_token="$cf_token" \
    terraform -chdir="$TF_DIR" apply -auto-approve -input=false

  # 5b. Backups bucket lifecycle (7-day expiry) -----------------------------
  # Set out-of-band rather than via Terraform: the aws provider's
  # aws_s3_bucket_lifecycle_configuration does a post-write read-back wait that
  # times out against Tigris (terraform-provider-aws#25939), so apply always
  # errored even though the rule applied. A plain put-bucket-lifecycle-configuration
  # is idempotent and has no read-back loop. Terraform still creates the bucket.
  log "Ensuring 7-day expiry on s3://${BACKUP_BUCKET}"
  AWS_ACCESS_KEY_ID="$tigris_id" AWS_SECRET_ACCESS_KEY="$tigris_secret" \
    aws s3api put-bucket-lifecycle-configuration \
      --bucket "$BACKUP_BUCKET" \
      --endpoint-url "$TIGRIS_ENDPOINT" \
      --lifecycle-configuration '{"Rules":[{"ID":"expire-after-7-days","Status":"Enabled","Filter":{},"Expiration":{"Days":7}}]}'

  # 5c. Tigris upload notification (webhook) --------------------------------
  # Point the uploads bucket at the backend's upload-processing-jobs webhook.
  # Out-of-band like 5b: a Tigris webhook (HTTP URL + Bearer token) is a
  # proprietary Tigris extension, not standard S3 — neither the tigris_bucket
  # Terraform resource nor `aws s3api put-bucket-notification-configuration`
  # (SNS/SQS/Lambda only) can express it, so we use the tigris CLI.
  # `set-notifications` writes the full config, so it's idempotent. --token is
  # the SAME secret seeded into hexagone-backend-secrets below, so what Tigris
  # sends (Authorization: Bearer …) matches what the backend validates. The
  # filter scopes it to the upload prefix so backups/other writes don't fire it.
  local app_hostname
  app_hostname="$(AWS_ACCESS_KEY_ID="$tigris_id" AWS_SECRET_ACCESS_KEY="$tigris_secret" \
    terraform -chdir="$TF_DIR" output -raw app_hostname)"
  log "Configuring Tigris notification on s3://${UPLOADS_BUCKET} -> https://${app_hostname}/api/upload-processing-jobs"
  tigris buckets set-notifications "$UPLOADS_BUCKET" \
    --access-key "$tigris_id" --access-secret "$tigris_secret" \
    --url "https://${app_hostname}/api/upload-processing-jobs" \
    --token "$upload_notification_secret" \
    --filter "WHERE \`key\` REGEXP \"^v1/uploads/\""

  # 6. Secrets (idempotent upsert) ------------------------------------------
  log "Upserting cloudflared-token secret"
  local tunnel_token
  tunnel_token="$(AWS_ACCESS_KEY_ID="$tigris_id" AWS_SECRET_ACCESS_KEY="$tigris_secret" \
    terraform -chdir="$TF_DIR" output -raw cloudflared_token)"
  k create secret generic cloudflared-token \
    --from-literal=token="$tunnel_token" \
    --dry-run=client -o yaml | k apply -f -

  log "Upserting hexagone-backend-secrets secret"
  k create secret generic hexagone-backend-secrets \
    --from-literal=AWS_ACCESS_KEY_ID="$tigris_id" \
    --from-literal=AWS_SECRET_ACCESS_KEY="$tigris_secret" \
    --from-literal=RESEND_API_KEY="$resend_key" \
    --from-literal=UPLOAD_NOTIFICATION_SECRET="$upload_notification_secret" \
    --dry-run=client -o yaml | k apply -f -

  # GHCR image-pull Secret (default ns): the deployments reference it via
  # imagePullSecrets to pull the private SHA-tagged images.
  log "Upserting ${GHCR_PULL_SECRET} image-pull secret"
  k create secret docker-registry "$GHCR_PULL_SECRET" \
    --docker-server=ghcr.io \
    --docker-username="$GHCR_USER" \
    --docker-password="$ghcr_pull_token" \
    --dry-run=client -o yaml | k apply -f -

  # Argo CD repository Secret (argocd ns): the read-only deploy key the repo-server
  # uses to clone the private repo over SSH. The argocd.argoproj.io/secret-type
  # label is what makes Argo treat it as a repo credential.
  #
  # Two macOS-Keychain gotchas to defuse, both of which yield Argo's "ssh: no key
  # found":
  #   1. `security -w` returns a MULTI-LINE secret (an SSH key is multi-line) as a
  #      HEX string, not the raw bytes — so kc() hands us hex, which is not a key.
  #   2. Go's SSH parser rejects a key without a trailing newline.
  # Handle both: if kc() gave us a real PEM, pass it through with exactly one
  # trailing newline; otherwise hex-decode what `security` dumped (xxd restores the
  # original bytes, trailing newline and all). --from-file avoids the newline-
  # stripping of --from-literal/`$()`.
  log "Upserting Argo CD repository secret"
  local tmpkey
  tmpkey="$(mktemp)"
  if printf '%s' "$argocd_deploy_key" | grep -q 'BEGIN OPENSSH'; then
    printf '%s\n' "$argocd_deploy_key" >"$tmpkey"
  else
    printf '%s' "$argocd_deploy_key" | xxd -r -p >"$tmpkey"
  fi
  k create secret generic hexagone-repo -n argocd \
    --from-literal=type=git \
    --from-literal=url="$REPO_SSH_URL" \
    --from-file=sshPrivateKey="$tmpkey" \
    --dry-run=client -o yaml \
    | k label --local -f - argocd.argoproj.io/secret-type=repository -o yaml \
    | k apply -f -
  rm -f "$tmpkey"

  # 7. Hand the app to Argo CD ----------------------------------------------
  # Argo owns the production overlay from here: it syncs it now and re-syncs on
  # every merge to main (CI bumps the image SHA). We apply only the Application CR
  # out-of-band; we do NOT `kubectl apply -k` the overlay ourselves.
  log "Applying Argo CD Application (Argo syncs the overlay from main)"
  k apply -f "$ARGOCD_APP_MANIFEST"

  # 8. Wait for readiness ---------------------------------------------------
  # Argo owns the app now: it creates the DB Cluster, backend, web and cloudflared.
  # Its app health aggregates all of them, so that's the real readiness signal —
  # wait on it first. If it never goes Healthy, the workloads may not exist yet, so
  # DON'T fall through to per-resource waits (they'd error NotFound on a Deployment
  # Argo hasn't synced) — surface the state and stop with a pointer to the sync.
  log "Waiting for Argo CD to sync the app Healthy (it creates the DB, backend, web, cloudflared)"
  if ! k -n argocd wait --for=jsonpath='{.status.health.status}'=Healthy \
       application/hexagone --timeout=420s; then
    warn "Argo app did not reach Healthy. The app workloads are created by Argo, so"
    warn "they may be missing or still progressing. Inspect the sync:"
    warn "    scripts/prod-stack.sh dashboard"
    warn "    kubectl --context $KUBE_CONTEXT -n argocd get application hexagone"
    k get pods 2>/dev/null || true
    return 1
  fi

  # Healthy ⇒ the resources exist; these waits are now race-free confirmation.
  log "Waiting for the database cluster"
  k wait --for=condition=Ready cluster/hexagone-db --timeout=300s
  for d in "${STATELESS_DEPLOYMENTS[@]}"; do
    log "Waiting for deploy/$d"
    k rollout status "deploy/$d" --timeout=300s
  done

  # 9. Summary --------------------------------------------------------------
  log "Stack is up:"
  k get pods
  printf '\n'
  log "Run 'scripts/prod-stack.sh status' anytime to re-check."
}

# --- down -------------------------------------------------------------------

cmd_down() {
  local skip_backup=0
  for arg in "$@"; do
    case "$arg" in
      --skip-backup) skip_backup=1 ;;
      *) die "unknown option for down: $arg (use --skip-backup)" ;;
    esac
  done

  need_cmd colima
  need_cmd kubectl
  if profile_running; then
    # Take an off-box backup before teardown so recovery never depends solely on
    # the host PVC. The PVC is still kept (for fast restarts), but there's now
    # always a fresh dump in Tigris too.
    if [ "$skip_backup" -eq 1 ]; then
      warn "Skipping pre-teardown backup (--skip-backup)"
    elif k get cluster hexagone-db >/dev/null 2>&1; then
      log "Backing up the database before teardown"
      k wait --for=condition=Ready cluster/hexagone-db --timeout=120s \
        || warn "DB cluster not Ready; attempting the backup anyway"
      # A failed backup ABORTS the teardown — the whole point is to not leave the
      # data only on the host PVC. Use --skip-backup to tear down without one.
      run_backup_job || die "pre-teardown backup FAILED — aborting 'down'. Fix the backup, or re-run with --skip-backup to tear down anyway."
      log "Off-box backup stored in s3://${BACKUP_BUCKET}"
    else
      die "no DB cluster found to back up — aborting 'down'. Re-run with --skip-backup if this is intentional."
    fi

    log "Deleting stateless workloads (database Cluster + data are kept)"
    k delete deployment "${STATELESS_DEPLOYMENTS[@]}" --ignore-not-found
    log "Stopping Colima profile '$COLIMA_PROFILE'"
    colima stop "$COLIMA_PROFILE"
  else
    log "Profile '$COLIMA_PROFILE' already stopped — nothing to tear down"
  fi
  log "Stack is down. Data and the Cloudflare tunnel persist; 'up' restores it."
}

# --- status -----------------------------------------------------------------

cmd_status() {
  need_cmd colima
  if ! profile_running; then
    log "Stack is DOWN (Colima profile '$COLIMA_PROFILE' stopped)."
    exit 0
  fi
  need_cmd kubectl
  log "Colima profile '$COLIMA_PROFILE' running. Cluster state:"
  k get pods
  printf '\n'
  k get cluster hexagone-db 2>/dev/null || warn "CNPG cluster hexagone-db not found"
  printf '\n'
  if k logs deploy/cloudflared --tail=20 2>/dev/null | grep -qi "registered"; then
    log "Cloudflare tunnel: registered (connected to edge)"
  else
    warn "Cloudflare tunnel: no 'registered' line in recent logs"
  fi
}

# --- backup -----------------------------------------------------------------

# Require the stack to be up with the DB cluster Ready. Used by backup/restore.
require_cluster_ready() {
  need_cmd colima
  need_cmd kubectl
  profile_running || die "stack is down — run 'scripts/prod-stack.sh up' first"
  k get cluster hexagone-db >/dev/null 2>&1 || die "cluster hexagone-db not found"
  log "Waiting for the database cluster to be Ready"
  k wait --for=condition=Ready cluster/hexagone-db --timeout=120s
}

# Fire a one-off run of the scheduled CronJob (so an ad-hoc dump is identical to a
# scheduled one) and wait for it. Fixed name + delete-first so manual runs don't
# accumulate. Returns non-zero if the job doesn't complete. Shared by backup/down.
run_backup_job() {
  log "Triggering an on-demand backup"
  k delete job hexagone-db-backup-manual --ignore-not-found
  k create job hexagone-db-backup-manual --from=cronjob/hexagone-db-backup
  log "Waiting for the backup job to finish"
  if ! k wait --for=condition=complete job/hexagone-db-backup-manual --timeout=600s; then
    k logs job/hexagone-db-backup-manual --all-containers --tail=50 || true
    return 1
  fi
  # The upload container's `aws s3 cp` line names the object it wrote.
  k logs job/hexagone-db-backup-manual --all-containers --tail=20 || true
}

cmd_backup() {
  require_cluster_ready
  run_backup_job || die "backup job did not complete"
  log "Backup complete."
}

# --- restore ----------------------------------------------------------------

cmd_restore() {
  local assume_yes=0 restore_from=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --yes | -y) assume_yes=1 ;;
      --restore-from)
        shift
        [ $# -gt 0 ] || die "--restore-from needs an object key (see 'tigris ls ${BACKUP_BUCKET}')"
        restore_from="$1"
        ;;
      --restore-from=*) restore_from="${1#--restore-from=}" ;;
      *) die "unknown option for restore: $1 (use --yes, --restore-from <key>)" ;;
    esac
    shift
  done

  require_cluster_ready

  # Default to the latest dump; --restore-from picks a specific object.
  local what="the latest backup"
  [ -n "$restore_from" ] && what="backup '$restore_from'"

  # Destructive: pg_restore --clean drops existing objects before reloading.
  if [ "$assume_yes" -ne 1 ]; then
    warn "Restore REPLACES the current database with ${what} (drops existing data)."
    printf 'Type "restore" to continue: '
    read -r reply || reply=""
    [ "$reply" = "restore" ] || die "aborted"
  fi

  log "Running restore job (${what} from s3://${BACKUP_BUCKET})"
  k delete job hexagone-db-restore --ignore-not-found
  if [ -n "$restore_from" ]; then
    # Inject BACKUP_KEY into the fetch init container so it restores that exact
    # object instead of the newest one (--local renders the manifest, no API call).
    kubectl set env --local -f "$RESTORE_MANIFEST" --containers=fetch \
      "BACKUP_KEY=$restore_from" -o yaml | k apply -f -
  else
    k apply -f "$RESTORE_MANIFEST"
  fi
  log "Waiting for the restore job to finish"
  if ! k wait --for=condition=complete job/hexagone-db-restore --timeout=600s; then
    k logs job/hexagone-db-restore --all-containers --tail=50 || true
    die "restore job did not complete"
  fi
  k logs job/hexagone-db-restore --all-containers --tail=30 || true

  log "Restarting backend to drop stale connections"
  k rollout restart deploy/hexagone-backend
  k rollout status deploy/hexagone-backend --timeout=180s
  log "Restore complete."
}

# --- dashboard --------------------------------------------------------------

# Launch the Argo CD web UI ON DEMAND. In Core mode there's no always-on UI server
# pod: `argocd admin dashboard` runs the API+UI as a local process that reads the
# cluster straight from the kubeconfig (no login, no Dex). Quit it (Ctrl-C) and the
# cluster is back to the 3 headless Argo pods.
cmd_dashboard() {
  need_cmd kubectl
  command -v argocd >/dev/null 2>&1 || die "argocd CLI not found — install with: brew install argocd"
  profile_running || die "stack is down — run 'scripts/prod-stack.sh up' first"

  local port="${1:-8080}"

  # `argocd admin dashboard` reads the kubeconfig's CURRENT context — unlike
  # kubectl it does NOT honour a --kube-context flag — and we deliberately never
  # make the prod context active (the VM starts with --activate=false so it can't
  # hijack your kubectl). So hand argocd a throwaway, self-contained kubeconfig
  # whose current-context IS the prod context, leaving ~/.kube/config untouched.
  local tmpkc
  tmpkc="$(mktemp)"
  trap 'rm -f "$tmpkc"' EXIT
  kubectl config view --raw --minify --context "$KUBE_CONTEXT" >"$tmpkc"

  # Bind to 127.0.0.1 explicitly: the default `localhost` can resolve to the IPv6
  # loopback only, which then refuses IPv4 (127.0.0.1) connections.
  log "Argo CD UI → http://127.0.0.1:${port}  (Ctrl-C to stop)"
  log "From your laptop over Tailscale, tunnel first:"
  log "    ssh -L ${port}:127.0.0.1:${port} <hexagone-mini-tailnet-ip>   # then open the URL above"
  KUBECONFIG="$tmpkc" argocd admin dashboard -n argocd --port "$port" --address 127.0.0.1
}

# --- Dispatch ---------------------------------------------------------------

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)"

case "${1:-}" in
  up)        shift; cmd_up "$@" ;;
  down)      shift; cmd_down "$@" ;;
  status)    shift; cmd_status "$@" ;;
  backup)    shift; cmd_backup "$@" ;;
  restore)   shift; cmd_restore "$@" ;;
  dashboard) shift; cmd_dashboard "$@" ;;
  *)
    cat >&2 <<EOF
Usage: scripts/prod-stack.sh <command>

  up                      Bring the whole stack up (idempotent). CI builds images; Argo deploys.
  down [--skip-backup]    Back up the DB off-box, then delete app workloads and stop the VM.
  status                  Show what's currently running.
  backup                  Take an on-demand Postgres dump now (e.g. before a risky migration).
  restore [--yes] [--restore-from <key>]
                          Restore the database (latest backup by default, or a specific
                          object key). Destructive; prompts unless --yes.
  dashboard [port]        Launch the Argo CD UI on demand (default port 8080; reach over Tailscale).
EOF
    exit 1
    ;;
esac
