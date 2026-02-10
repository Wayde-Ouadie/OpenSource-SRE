#!/usr/bin/env bash
# Smoke test: Basic health checks for all services
set -euo pipefail

DC="docker compose -f deployment/docker-compose.yml --env-file deployment/.env"

echo "==> Running smoke tests..."

FAILED=0

check_health() {
    local service="$1"
    local url="$2"
    echo -n "  Checking $service... "
    if curl -fsS --connect-timeout 3 --max-time 5 "$url" >/dev/null 2>&1; then
        echo "✓ OK"
    else
        echo "✗ FAILED"
        FAILED=1
    fi
}

# Health check via docker-compose exec (for services without host port mapping)
check_health_internal() {
    local service="$1"
    local port="$2"
    echo -n "  Checking $service (internal)... "
    if $DC exec -T "$service" curl -fsS --connect-timeout 3 --max-time 5 "http://localhost:${port}/health" >/dev/null 2>&1; then
        echo "✓ OK"
    else
        echo "✗ FAILED"
        FAILED=1
    fi
}

echo
echo "Service Health Checks:"
check_health "web-ui" "http://localhost:8080/health"
check_health_internal "incident-management" "8002"
check_health_internal "alert-ingestion" "8001"
check_health "oncall-service" "http://localhost:8003/health"
check_health "notification-service" "http://localhost:8004/health"
check_health "gateway" "http://localhost:8010/health"
check_health "prometheus" "http://localhost:9090/-/healthy"
check_health "grafana" "http://localhost:3000/api/health"

echo
if [ $FAILED -eq 0 ]; then
    echo "✓ All smoke tests passed!"
    exit 0
else
    echo "✗ Some smoke tests failed"
    exit 1
fi
