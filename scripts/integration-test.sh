#!/usr/bin/env bash

echo "==> Running integration tests..."

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

test_case "Send test alert" \
    curl -fsS --connect-timeout 3 --max-time 5 \
    -X POST http://localhost:8001/api/v1/alerts \
    -H 'Content-Type: application/json' \
    -d '{"service":"test-service","severity":"high","message":"Integration test alert","labels":{"environment":"test"}}'

test_case "List incidents" \
    curl -fsS --connect-timeout 3 --max-time 5 \
    http://localhost:8002/api/v1/incidents

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

# Test 7: Check metrics endpoints
for port in 8001 8002 8003 8004 8010 8011; do
    test_case "Check metrics at :$port" \
        curl -fsS --connect-timeout 3 --max-time 5 \
        http://localhost:$port/metrics
done

echo
if [ $FAILED -eq 0 ]; then
    echo "✓ All integration tests passed!"
    exit 0
else
    echo "✗ Some integration tests failed"
    exit 1
fi
