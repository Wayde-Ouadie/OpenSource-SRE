#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Automated Rollback Script
#
# Performs a safe rolling deploy of a service with automatic rollback:
#   1. Tags the currently running image as :rollback
#   2. Builds & deploys the new version
#   3. Runs health checks against the new container(s)
#   4. If health fails → automatically rolls back to the :rollback image
#
# Usage:
#   ./scripts/rollback.sh <service>                # Build & deploy with rollback safety
#   ./scripts/rollback.sh <service> --simulate-failure  # Inject failure to test rollback
#
# Examples:
#   ./scripts/rollback.sh incident-management
#   ./scripts/rollback.sh alert-ingestion --simulate-failure
# ---------------------------------------------------------------------------
set -euo pipefail

SERVICE="${1:?Usage: $0 <service> [--simulate-failure]}"
SIMULATE_FAILURE="${2:-}"
DC="docker compose -f deployment/docker-compose.yml --env-file deployment/.env"

# Health check settings
HEALTH_RETRIES=12
HEALTH_INTERVAL=5
HEALTH_TIMEOUT=3

# Colour helpers
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

banner() { echo -e "\n${CYAN}════════════════════════════════════════════════════════════${NC}"; echo -e "${CYAN}  $1${NC}"; echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}\n"; }
info()   { echo -e "  ${GREEN}✓${NC} $1"; }
warn()   { echo -e "  ${YELLOW}⚠${NC} $1"; }
fail()   { echo -e "  ${RED}✗${NC} $1"; }
step()   { echo -e "  ${BOLD}→${NC} $1"; }

# Map service name to image
get_image() {
  $DC config --format json 2>/dev/null | \
    python3 -c "import sys,json; cfg=json.load(sys.stdin); print(cfg['services']['$1']['image'])" 2>/dev/null || echo ""
}

# Map service name to internal port
get_port() {
  case "$1" in
    incident-management) echo 8002 ;;
    alert-ingestion)     echo 8001 ;;
    oncall-service)      echo 8003 ;;
    notification-service)echo 8004 ;;
    gateway)             echo 8000 ;;
    monitoring)          echo 8000 ;;
    web-ui)              echo 8080 ;;
    *) echo ""; fail "Unknown service: $1"; exit 1 ;;
  esac
}

# Perform health checks against running containers
check_health() {
  local svc="$1"
  local port="$2"
  local attempt=1

  while [ $attempt -le $HEALTH_RETRIES ]; do
    echo -ne "  Health check attempt $attempt/$HEALTH_RETRIES...\r"

    # Get all container IDs for the service
    CONTAINER_IDS=$($DC ps -q "$svc" 2>/dev/null || true)
    if [ -z "$CONTAINER_IDS" ]; then
      sleep "$HEALTH_INTERVAL"
      attempt=$((attempt + 1))
      continue
    fi

    ALL_OK=true
    for CID in $CONTAINER_IDS; do
      RESP=$(docker exec "$CID" curl -fsS --max-time "$HEALTH_TIMEOUT" "http://localhost:${port}/health" 2>/dev/null || echo "FAIL")
      if ! echo "$RESP" | grep -q '"status"'; then
        ALL_OK=false
        break
      fi
    done

    if $ALL_OK; then
      echo ""
      return 0
    fi

    sleep "$HEALTH_INTERVAL"
    attempt=$((attempt + 1))
  done

  echo ""
  return 1
}

IMAGE=$(get_image "$SERVICE")
PORT=$(get_port "$SERVICE")
ROLLBACK_TAG="${IMAGE%:*}:rollback"

if [ -z "$IMAGE" ]; then
  fail "Could not determine image for service '$SERVICE'"
  exit 1
fi

banner "AUTOMATED DEPLOY WITH ROLLBACK — $SERVICE"
echo -e "  ${BOLD}Service:${NC}      $SERVICE"
echo -e "  ${BOLD}Image:${NC}        $IMAGE"
echo -e "  ${BOLD}Rollback tag:${NC} $ROLLBACK_TAG"
echo -e "  ${BOLD}Health port:${NC}  $PORT"
[ -n "$SIMULATE_FAILURE" ] && echo -e "  ${RED}${BOLD}Mode:${NC}         ${RED}SIMULATED FAILURE${NC}"
echo ""

# ---------------------------------------------------------------------------
banner "STEP 1 — Save current image as rollback snapshot"
# ---------------------------------------------------------------------------

if docker image inspect "$IMAGE" >/dev/null 2>&1; then
  docker tag "$IMAGE" "$ROLLBACK_TAG"
  info "Tagged $IMAGE → $ROLLBACK_TAG"
else
  warn "No existing image found for $IMAGE — first deploy (no rollback possible)"
fi

# ---------------------------------------------------------------------------
banner "STEP 2 — Build new image"
# ---------------------------------------------------------------------------

step "Building $SERVICE..."
$DC build "$SERVICE" 2>&1 | tail -5 | sed 's/^/  /'
info "Build complete"

NEW_DIGEST=$(docker image inspect "$IMAGE" --format '{{.Id}}' 2>/dev/null | cut -c8-19)
info "New image digest: $NEW_DIGEST"

# ---------------------------------------------------------------------------
# Simulate failure: replace entrypoint so the container exits immediately
# ---------------------------------------------------------------------------
if [ "$SIMULATE_FAILURE" = "--simulate-failure" ]; then
  banner "⚡ INJECTING SIMULATED FAILURE"
  warn "Creating a broken image to test rollback..."

  # Build a throwaway broken image on top of the current one
  BROKEN_DOCKERFILE=$(mktemp)
  cat > "$BROKEN_DOCKERFILE" <<EOF
FROM $IMAGE
CMD ["sh", "-c", "echo 'SIMULATED CRASH' && exit 1"]
EOF
  docker build -f "$BROKEN_DOCKERFILE" -t "$IMAGE" . --quiet 2>/dev/null
  rm -f "$BROKEN_DOCKERFILE"
  warn "Injected broken CMD into $IMAGE"
fi

# ---------------------------------------------------------------------------
banner "STEP 3 — Deploy new version"
# ---------------------------------------------------------------------------

step "Stopping old container(s)..."
$DC stop "$SERVICE" 2>&1 | sed 's/^/  /'

step "Starting new container(s)..."
$DC up -d "$SERVICE" 2>&1 | sed 's/^/  /'

# ---------------------------------------------------------------------------
banner "STEP 4 — Health verification"
# ---------------------------------------------------------------------------

step "Checking health (up to $((HEALTH_RETRIES * HEALTH_INTERVAL))s)..."

if check_health "$SERVICE" "$PORT"; then
  # =========================================================================
  banner "✅ DEPLOY SUCCESSFUL"
  # =========================================================================
  info "$SERVICE is healthy with the new version"
  info "Rollback image preserved at: $ROLLBACK_TAG"

  # Show running containers
  echo ""
  $DC ps "$SERVICE"

  # Clean up old rollback tag (optional, keep for manual rollback)
  echo ""
  info "To manually rollback later:  docker tag $ROLLBACK_TAG $IMAGE && $DC up -d $SERVICE"
  echo ""
  exit 0
else
  # =========================================================================
  banner "❌ HEALTH CHECK FAILED — INITIATING ROLLBACK"
  # =========================================================================
  fail "New $SERVICE failed health checks after $((HEALTH_RETRIES * HEALTH_INTERVAL))s"
  echo ""

  # Check if we have a rollback image
  if docker image inspect "$ROLLBACK_TAG" >/dev/null 2>&1; then
    step "Restoring previous image..."
    docker tag "$ROLLBACK_TAG" "$IMAGE"
    info "Restored $ROLLBACK_TAG → $IMAGE"

    step "Stopping failed container(s)..."
    $DC stop "$SERVICE" 2>&1 | sed 's/^/  /'

    step "Starting rollback container(s)..."
    $DC up -d "$SERVICE" 2>&1 | sed 's/^/  /'

    echo ""
    step "Verifying rollback health..."
    sleep 5

    if check_health "$SERVICE" "$PORT"; then
      info "Rollback successful — $SERVICE is healthy with previous version"
      echo ""
      $DC ps "$SERVICE"
    else
      fail "CRITICAL: Rollback also failed! Manual intervention required."
      $DC logs --tail 20 "$SERVICE" 2>/dev/null | sed 's/^/  /'
    fi
  else
    fail "No rollback image available ($ROLLBACK_TAG not found)"
    fail "Manual intervention required"
    $DC logs --tail 20 "$SERVICE" 2>/dev/null | sed 's/^/  /'
  fi

  echo ""
  exit 1
fi
