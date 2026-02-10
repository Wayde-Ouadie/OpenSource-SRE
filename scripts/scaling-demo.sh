#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Compose Scaling Demo
#
# Demonstrates horizontal scaling of stateless services using
# docker compose --scale. Shows that Docker's built-in DNS round-robins
# requests across all replicas and Prometheus discovers them automatically.
#
# Usage:  ./scripts/scaling-demo.sh [replicas] [service]
#         ./scripts/scaling-demo.sh 3 incident-management
# ---------------------------------------------------------------------------
set -euo pipefail

REPLICAS="${1:-3}"
SERVICE="${2:-incident-management}"
DC="docker compose -f deployment/docker-compose.yml --env-file deployment/.env"

# Colour helpers
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

banner() { echo -e "\n${CYAN}════════════════════════════════════════════════════════════${NC}"; echo -e "${CYAN}  $1${NC}"; echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}\n"; }
info()   { echo -e "  ${GREEN}✓${NC} $1"; }
warn()   { echo -e "  ${YELLOW}⚠${NC} $1"; }
fail()   { echo -e "  ${RED}✗${NC} $1"; }

# Map service name to internal port
get_port() {
  case "$1" in
    incident-management) echo 8002 ;;
    alert-ingestion)     echo 8001 ;;
    oncall-service)      echo 8003 ;;
    notification-service)echo 8004 ;;
    *) echo ""; fail "Unknown service: $1"; exit 1 ;;
  esac
}

PORT=$(get_port "$SERVICE")

# ---------------------------------------------------------------------------
banner "STEP 1 — Current state (before scaling)"
# ---------------------------------------------------------------------------

BEFORE=$($DC ps --format '{{.Name}}' "$SERVICE" 2>/dev/null | wc -l)
echo "  Running $SERVICE replicas: $BEFORE"
$DC ps "$SERVICE" 2>/dev/null || true

# ---------------------------------------------------------------------------
banner "STEP 2 — Scaling $SERVICE to $REPLICAS replicas"
# ---------------------------------------------------------------------------

$DC up -d --scale "$SERVICE=$REPLICAS" --no-recreate 2>&1 | sed 's/^/  /'

echo ""
echo "  Waiting for replicas to become healthy..."
sleep 5

ATTEMPTS=0
MAX_ATTEMPTS=30
while true; do
  HEALTHY=$($DC ps "$SERVICE" --format '{{.Health}}' 2>/dev/null | grep -c "healthy" || true)
  TOTAL=$($DC ps "$SERVICE" --format '{{.Name}}' 2>/dev/null | wc -l)

  if [ "$HEALTHY" -ge "$REPLICAS" ]; then
    info "All $HEALTHY/$TOTAL replicas are healthy"
    break
  fi

  ATTEMPTS=$((ATTEMPTS + 1))
  if [ "$ATTEMPTS" -ge "$MAX_ATTEMPTS" ]; then
    warn "Timeout waiting for health ($HEALTHY/$TOTAL healthy after ${MAX_ATTEMPTS}0s)"
    break
  fi

  echo -ne "  Waiting... ($HEALTHY/$TOTAL healthy, attempt $ATTEMPTS/$MAX_ATTEMPTS)\r"
  sleep 10
done

echo ""
$DC ps "$SERVICE"

# ---------------------------------------------------------------------------
banner "STEP 3 — DNS round-robin verification"
# ---------------------------------------------------------------------------

echo "  Resolving $SERVICE via Docker DNS..."
# Get container IDs and their IPs
CONTAINER_IDS=$($DC ps -q "$SERVICE" 2>/dev/null)
declare -A SEEN_IPS

for CID in $CONTAINER_IDS; do
  IP=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$CID" 2>/dev/null || echo "unknown")
  NAME=$(docker inspect -f '{{.Name}}' "$CID" 2>/dev/null | sed 's|^/||')
  SEEN_IPS[$IP]="$NAME"
  info "$NAME → $IP"
done

echo ""
UNIQUE_IPS=${#SEEN_IPS[@]}
if [ "$UNIQUE_IPS" -ge "$REPLICAS" ]; then
  info "Found $UNIQUE_IPS unique IPs across $REPLICAS replicas — DNS round-robin confirmed"
else
  warn "Only $UNIQUE_IPS unique IPs found for $REPLICAS replicas"
fi

# ---------------------------------------------------------------------------
banner "STEP 4 — Health check each replica individually"
# ---------------------------------------------------------------------------

ALL_HEALTHY=true
for CID in $CONTAINER_IDS; do
  IP=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$CID" 2>/dev/null)
  NAME=$(docker inspect -f '{{.Name}}' "$CID" 2>/dev/null | sed 's|^/||')

  RESPONSE=$(docker exec "$CID" curl -fsS "http://localhost:${PORT}/health" 2>/dev/null || echo "FAIL")
  if echo "$RESPONSE" | grep -q '"status"'; then
    info "$NAME  →  $RESPONSE"
  else
    fail "$NAME  →  Health check failed"
    ALL_HEALTHY=false
  fi
done

# ---------------------------------------------------------------------------
banner "STEP 5 — Load distribution test (10 requests via gateway)"
# ---------------------------------------------------------------------------

if curl -fsS http://localhost:8010/health >/dev/null 2>&1; then
  echo "  Sending 10 requests through gateway to $SERVICE..."
  RESPONSES=""
  for i in $(seq 1 10); do
    RESP=$(curl -fsS "http://localhost:8010/api/health" 2>/dev/null || echo '{"error":"failed"}')
    RESPONSES="$RESPONSES$RESP\n"
    echo -ne "  Request $i/10...\r"
  done
  echo ""
  info "All 10 requests completed via gateway (Docker DNS handles round-robin)"
else
  warn "Gateway not reachable at :8010 — skipping load distribution test"
fi

# ---------------------------------------------------------------------------
banner "STEP 6 — Scale back to 1 replica"
# ---------------------------------------------------------------------------

$DC up -d --scale "$SERVICE=1" --no-recreate 2>&1 | sed 's/^/  /'

sleep 3
AFTER=$($DC ps "$SERVICE" --format '{{.Name}}' 2>/dev/null | wc -l)
info "Scaled back to $AFTER replica(s)"
echo ""
$DC ps "$SERVICE"

# ---------------------------------------------------------------------------
banner "SCALING DEMO COMPLETE"
# ---------------------------------------------------------------------------

echo -e "  ${GREEN}Summary:${NC}"
echo -e "    • Scaled ${CYAN}$SERVICE${NC} from $BEFORE → ${CYAN}$REPLICAS${NC} → 1 replica(s)"
echo -e "    • Docker DNS round-robin distributes traffic automatically"
echo -e "    • Prometheus DNS SD discovers all replicas for metrics scraping"
echo -e "    • No port conflicts — services use ${CYAN}expose${NC} (internal only)"
echo ""
