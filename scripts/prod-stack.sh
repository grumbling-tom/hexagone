#!/usr/bin/env bash
#
# prod-stack.sh — spin the Hexagone production stack up and down on the Mac mini
# (Colima VM -> k3s). One command replaces the manual runbook in
# infra/k8s/README.md + infra/terraform/README.md.
#
# Usage:
#   scripts/prod-stack.sh up [--build]   bring the whole stack up (idempotent)
#   scripts/prod-stack.sh down            delete app workloads, stop the VM (data kept)
#   scripts/prod-stack.sh status          show what's running
#
# `up` folds in the one-time bootstrap (CNPG operator, Cloudflare tunnel) and is
# safe to re-run. `--build` forces both images to rebuild; without it they're
# built only when missing. `down` deliberately leaves the CNPG database Cluster
# (and its PVC) and the Cloudflare tunnel in place, so `up` restores all data.

set -euo pipefail

# --- Config -----------------------------------------------------------------

# CloudNativePG operator release (installed out-of-band, never in the overlay —
# see infra/k8s/CLAUDE.md). Bump alongside the version in infra/k8s/README.md.
CNPG_VERSION="1.29.0"
CNPG_BRANCH="release-1.29"
CNPG_MANIFEST="https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/${CNPG_BRANCH}/releases/cnpg-${CNPG_VERSION}.yaml"

TIGRIS_ENDPOINT="https://t3.storage.dev"
TF_STATE_BUCKET="hexagone-tfstate"
TF_DIR="infra/terraform"
K8S_OVERLAY="infra/k8s/production"

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

# Read a secret from the macOS login Keychain (account = $USER), matching the
# convention in infra/terraform/README.md.
kc() {
  security find-generic-password -a "$USER" -s "$1" -w 2>/dev/null \
    || die "missing Keychain entry '$1'. Add it with:
    security add-generic-password -a \"\$USER\" -s $1 -w"
}

colima_running() {
  colima status 2>/dev/null | grep -qi running
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
  if colima_running; then
    log "Colima already running"
  else
    log "Starting Colima"
    colima start
  fi
  log "Waiting for the k3s node to be Ready"
  kubectl wait --for=condition=Ready nodes --all --timeout=120s

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
  if kubectl get deploy cnpg-controller-manager -n cnpg-system >/dev/null 2>&1; then
    log "CNPG operator already installed"
  else
    log "Installing CNPG operator ${CNPG_VERSION}"
    kubectl apply --server-side -f "$CNPG_MANIFEST"
    kubectl -n cnpg-system rollout status deploy/cnpg-controller-manager --timeout=180s
  fi

  # 5. Images (build-if-missing; --build forces) ----------------------------
  build_image() {
    local image="$1" context="$2"
    if [ "$force_build" -eq 1 ] || ! docker image inspect "$image" >/dev/null 2>&1; then
      log "Building $image"
      docker build -t "$image" "$context"
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
  kubectl create secret generic cloudflared-token \
    --from-literal=token="$tunnel_token" \
    --dry-run=client -o yaml | kubectl apply -f -

  log "Upserting hexagone-backend-secrets secret"
  kubectl create secret generic hexagone-backend-secrets \
    --from-literal=AWS_ACCESS_KEY_ID="$tigris_id" \
    --from-literal=AWS_SECRET_ACCESS_KEY="$tigris_secret" \
    --from-literal=RESEND_API_KEY="$resend_key" \
    --dry-run=client -o yaml | kubectl apply -f -

  # 8. Apply overlay --------------------------------------------------------
  log "Applying app overlay ($K8S_OVERLAY)"
  kubectl apply -k "$K8S_OVERLAY"

  # 9. Wait for readiness ---------------------------------------------------
  log "Waiting for the database cluster"
  kubectl wait --for=condition=Ready cluster/hexagone-db --timeout=300s
  for d in "${STATELESS_DEPLOYMENTS[@]}"; do
    log "Waiting for deploy/$d"
    kubectl rollout status "deploy/$d" --timeout=300s
  done

  # 10. Summary -------------------------------------------------------------
  log "Stack is up:"
  kubectl get pods
  printf '\n'
  log "Run 'scripts/prod-stack.sh status' anytime to re-check."
}

# --- down -------------------------------------------------------------------

cmd_down() {
  need_cmd colima
  need_cmd kubectl
  if colima_running; then
    log "Deleting stateless workloads (database Cluster + data are kept)"
    kubectl delete deployment "${STATELESS_DEPLOYMENTS[@]}" --ignore-not-found
    log "Stopping Colima"
    colima stop
  else
    log "Colima already stopped — nothing to tear down"
  fi
  log "Stack is down. Data and the Cloudflare tunnel persist; 'up' restores it."
}

# --- status -----------------------------------------------------------------

cmd_status() {
  need_cmd colima
  if ! colima_running; then
    log "Stack is DOWN (Colima stopped)."
    exit 0
  fi
  need_cmd kubectl
  log "Colima running. Cluster state:"
  kubectl get pods
  printf '\n'
  kubectl get cluster hexagone-db 2>/dev/null || warn "CNPG cluster hexagone-db not found"
  printf '\n'
  if kubectl logs deploy/cloudflared --tail=20 2>/dev/null | grep -qi "registered"; then
    log "Cloudflare tunnel: registered (connected to edge)"
  else
    warn "Cloudflare tunnel: no 'registered' line in recent logs"
  fi
}

# --- Dispatch ---------------------------------------------------------------

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)"

case "${1:-}" in
  up)     shift; cmd_up "$@" ;;
  down)   shift; cmd_down "$@" ;;
  status) shift; cmd_status "$@" ;;
  *)
    cat >&2 <<EOF
Usage: scripts/prod-stack.sh <command>

  up [--build]   Bring the whole stack up (idempotent). --build forces image rebuild.
  down           Delete app workloads and stop the VM (database + tunnel persist).
  status         Show what's currently running.
EOF
    exit 1
    ;;
esac
