#!/usr/bin/env bash

echo "==> Running integration tests..."

DC="docker compose -f deployment/docker-compose.yml --env-file deployment/.env"
FAILED=0

test_case() {
    local name="$1"
    shift
    echo -n "  $name... "
    if "$@" >/dev/null 2>&1; then
        echo "✓ PASS"
    else
        echo "✗ FAIL"
        FAILED=1
    fi
}

# Internal test via docker exec (for services without host port mapping)
test_case_internal() {
    local name="$1"
    local service="$2"
    shift 2
    echo -n "  $name... "
    if $DC exec -T "$service" "$@" >/dev/null 2>&1; then
        echo "✓ PASS"
    else
        echo "✗ FAIL"
        FAILED=1
    fi
}

echo
echo "API Integration Tests:"

test_case "Create on-call schedule" \
    curl -fsS --connect-timeout 3 --max-time 5 \
    -X POST http://localhost:8003/api/v1/schedules \
    -H 'Content-Type: application/json' \
    -d '{"team":"platform-engineering","primary":["alice","bob"],"secondary":["carol"],"rotation":"weekly"}'

test_case "Get current on-call" \
    curl -fsS --connect-timeout 3 --max-time 5 \
    "http://localhost:8003/api/v1/oncall/current?team=platform-engineering"

# Alert ingestion via nginx proxy (no host port)
test_case "Send test alert (via nginx)" \
    curl -fsS --connect-timeout 3 --max-time 5 \
    -X POST http://localhost:8080/api/v1/alerts \
    -H 'Content-Type: application/json' \
    -d '{"service":"test-service","severity":"high","message":"Integration test alert","labels":{"environment":"test"}}'

# Incident management via nginx proxy (no host port)
test_case "List incidents (via nginx)" \
    curl -fsS --connect-timeout 3 --max-time 5 \
    http://localhost:8080/api/v1/incidents

# Test 5: Send notification
test_case "Send notification" \
    curl -fsS --connect-timeout 3 --max-time 5 \
    -X POST http://localhost:8004/api/v1/notify \
    -H 'Content-Type: application/json' \
    -d '{"incident_id":"test-123","message":"Test notification","channel":"mock"}'

# Test 6: Check Prometheus targets
test_case "Check Prometheus scrape targets" \
    curl -fsS --connect-timeout 3 --max-time 5 \
    http://localhost:9090/api/v1/targets

# Test 7: Check metrics on services with host ports
for port in 8003 8004 8010; do
    test_case "Check metrics at :$port" \
        curl -fsS --connect-timeout 3 --max-time 5 \
        http://localhost:$port/metrics
done

# Test 8: Check metrics on internal services via docker exec
test_case_internal "Check metrics (incident-management)" "incident-management" \
    curl -fsS --connect-timeout 3 --max-time 5 http://localhost:8002/metrics

test_case_internal "Check metrics (alert-ingestion)" "alert-ingestion" \
    curl -fsS --connect-timeout 3 --max-time 5 http://localhost:8001/metrics

echo
if [ $FAILED -eq 0 ]; then
    echo "✓ All integration tests passed!"
    exit 0
else
    echo "✗ Some integration tests failed"
    exit 1
fi
