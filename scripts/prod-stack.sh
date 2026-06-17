#!/usr/bin/env bash
#
# prod-stack.sh — spin the Hexagone production stack up and down on the Mac mini
# (Colima VM -> k3s). One command replaces the manual runbook in
# infra/k8s/README.md + infra/terraform/README.md.
#
# Usage:
#   scripts/prod-stack.sh up [--build]    bring the whole stack up (idempotent)
#   scripts/prod-stack.sh down            delete app workloads, stop the VM (data kept)
#   scripts/prod-stack.sh status          show what's running
#   scripts/prod-stack.sh backup          take an on-demand Postgres dump now
#   scripts/prod-stack.sh restore [--yes] restore the DB from the latest backup
#
# `up` folds in the one-time bootstrap (CNPG operator, Cloudflare tunnel) and is
# safe to re-run. `--build` forces both images to rebuild; without it they're
# built only when missing. `down` deliberately leaves the CNPG database Cluster
# (and its PVC) and the Cloudflare tunnel in place, so `up` restores all data.
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

TIGRIS_ENDPOINT="https://t3.storage.dev"
TF_STATE_BUCKET="hexagone-tfstate"
TF_DIR="infra/terraform"
K8S_OVERLAY="infra/k8s/production"

# Postgres backups: dedicated Tigris bucket (created in infra/terraform/storage.tf
# with a 7-day expiry rule) + the on-demand restore Job (kept out of the overlay).
BACKUP_BUCKET="hexagone-db-backups"
RESTORE_MANIFEST="infra/k8s/jobs/db-restore.yaml"

BACKEND_IMAGE="hexagone-backend:latest"
WEB_IMAGE="hexagone-web:latest"

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
  local force_build=0
  for arg in "$@"; do
    case "$arg" in
      --build) force_build=1 ;;
      *) die "unknown option for up: $arg (use --build)" ;;
    esac
  done

  # 1. Preflight ------------------------------------------------------------
  log "Preflight: checking tools and Keychain entries"
  for c in colima kubectl docker terraform aws security; do need_cmd "$c"; done
  # Verify all four Keychain entries up front so we fail fast, not mid-apply.
  local cf_token tigris_id tigris_secret resend_key
  cf_token="$(kc cloudflare-api-token)"
  tigris_id="$(kc hexagone-tigris-access-key-id)"
  tigris_secret="$(kc hexagone-tigris-secret-access-key)"
  resend_key="$(kc hexagone-resend-api-key)"

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

  # 4. CNPG operator (idempotent) -------------------------------------------
  if k get deploy cnpg-controller-manager -n cnpg-system >/dev/null 2>&1; then
    log "CNPG operator already installed"
  else
    log "Installing CNPG operator ${CNPG_VERSION}"
    k apply --server-side -f "$CNPG_MANIFEST"
    k -n cnpg-system rollout status deploy/cnpg-controller-manager --timeout=180s
  fi

  # 5. Images (build-if-missing; --build forces) ----------------------------
  # Build against the prod profile's docker daemon so k3s sees the image in its
  # own store (imagePullPolicy: IfNotPresent) with no registry/import step.
  build_image() {
    local image="$1" context="$2"
    if [ "$force_build" -eq 1 ] || ! dkr image inspect "$image" >/dev/null 2>&1; then
      log "Building $image"
      dkr build -t "$image" "$context"
    else
      log "$image present (use --build to rebuild)"
    fi
  }
  build_image "$BACKEND_IMAGE" apps/backend
  build_image "$WEB_IMAGE" apps/web

  # 6. Terraform (idempotent apply) -----------------------------------------
  log "Applying Cloudflare tunnel via Terraform"
  AWS_ACCESS_KEY_ID="$tigris_id" AWS_SECRET_ACCESS_KEY="$tigris_secret" \
  TF_VAR_cloudflare_api_token="$cf_token" \
    terraform -chdir="$TF_DIR" init -input=false >/dev/null
  AWS_ACCESS_KEY_ID="$tigris_id" AWS_SECRET_ACCESS_KEY="$tigris_secret" \
  TF_VAR_cloudflare_api_token="$cf_token" \
    terraform -chdir="$TF_DIR" apply -auto-approve -input=false

  # 7. Secrets (idempotent upsert) ------------------------------------------
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
    --dry-run=client -o yaml | k apply -f -

  # 8. Apply overlay --------------------------------------------------------
  log "Applying app overlay ($K8S_OVERLAY)"
  k apply -k "$K8S_OVERLAY"

  # 9. Wait for readiness ---------------------------------------------------
  log "Waiting for the database cluster"
  k wait --for=condition=Ready cluster/hexagone-db --timeout=300s
  for d in "${STATELESS_DEPLOYMENTS[@]}"; do
    log "Waiting for deploy/$d"
    k rollout status "deploy/$d" --timeout=300s
  done

  # 10. Summary -------------------------------------------------------------
  log "Stack is up:"
  k get pods
  printf '\n'
  log "Run 'scripts/prod-stack.sh status' anytime to re-check."
}

# --- down -------------------------------------------------------------------

cmd_down() {
  need_cmd colima
  need_cmd kubectl
  if profile_running; then
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

cmd_backup() {
  require_cluster_ready
  # Fire a one-off run of the scheduled CronJob, so an ad-hoc dump is identical to
  # a scheduled one. Fixed name + delete-first so manual runs don't accumulate.
  log "Triggering an on-demand backup"
  k delete job hexagone-db-backup-manual --ignore-not-found
  k create job hexagone-db-backup-manual --from=cronjob/hexagone-db-backup
  log "Waiting for the backup job to finish"
  if ! k wait --for=condition=complete job/hexagone-db-backup-manual --timeout=300s; then
    k logs job/hexagone-db-backup-manual --all-containers --tail=50 || true
    die "backup job did not complete"
  fi
  # The upload container's `aws s3 cp` line names the object it wrote.
  k logs job/hexagone-db-backup-manual --all-containers --tail=20 || true
  log "Backup complete."
}

# --- restore ----------------------------------------------------------------

cmd_restore() {
  local assume_yes=0
  for arg in "$@"; do
    case "$arg" in
      --yes | -y) assume_yes=1 ;;
      *) die "unknown option for restore: $arg (use --yes)" ;;
    esac
  done

  require_cluster_ready

  # Destructive: pg_restore --clean drops existing objects before reloading.
  if [ "$assume_yes" -ne 1 ]; then
    warn "Restore REPLACES the current database with the latest backup (drops existing data)."
    printf 'Type "restore" to continue: '
    read -r reply || reply=""
    [ "$reply" = "restore" ] || die "aborted"
  fi

  log "Running restore job (latest dump from s3://${BACKUP_BUCKET})"
  k delete job hexagone-db-restore --ignore-not-found
  k apply -f "$RESTORE_MANIFEST"
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

# --- Dispatch ---------------------------------------------------------------

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)"

case "${1:-}" in
  up)      shift; cmd_up "$@" ;;
  down)    shift; cmd_down "$@" ;;
  status)  shift; cmd_status "$@" ;;
  backup)  shift; cmd_backup "$@" ;;
  restore) shift; cmd_restore "$@" ;;
  *)
    cat >&2 <<EOF
Usage: scripts/prod-stack.sh <command>

  up [--build]    Bring the whole stack up (idempotent). --build forces image rebuild.
  down            Delete app workloads and stop the VM (database + tunnel persist).
  status          Show what's currently running.
  backup          Take an on-demand Postgres dump now (e.g. before a risky migration).
  restore [--yes] Restore the database from the latest backup. Destructive; prompts unless --yes.
EOF
    exit 1
    ;;
esac
