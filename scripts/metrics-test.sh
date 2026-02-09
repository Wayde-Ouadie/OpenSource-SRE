#!/usr/bin/env bash
# Metrics test: Verify all required Prometheus metrics are exposed
set -euo pipefail

echo "==> Testing Prometheus metrics compliance..."
echo

FAILED=0

check_metric() {
    local service="$1"
    local port="$2"
    local metric_pattern="$3"
    local url="http://localhost:$port/metrics"
    
    echo -n "  $service - $metric_pattern... "
    if curl -fsS --connect-timeout 3 --max-time 5 "$url" 2>/dev/null | grep -q "$metric_pattern"; then
        echo "✓ OK"
    else
        echo "✗ MISSING"
        FAILED=1
    fi
}

echo "Required Custom Metrics:"
check_metric "incident-management" 8002 "incidents_total"
check_metric "incident-management" 8002 "incident_mtta_seconds"
check_metric "incident-management" 8002 "incident_mttr_seconds"
check_metric "alert-ingestion" 8001 "alerts_received_total"
check_metric "alert-ingestion" 8001 "alerts_correlated_total"
check_metric "notification" 8004 "oncall_notifications_sent_total"
check_metric "oncall" 8003 "oncall_current"

echo
echo "Process Metrics (should exist on all services):"
for port in 8001 8002 8003 8004 8010 8011; do
    check_metric "service:$port" "$port" "process_cpu_seconds_total"
done

echo
echo "Prometheus Scrape Targets:"
TARGETS=$(curl -fsS http://localhost:9090/api/v1/targets 2>/dev/null)
echo "$TARGETS" | grep -o '"job":"[^"]*"' | sort -u | sed 's/^/  /'

echo
if [ $FAILED -eq 0 ]; then
    echo "✓ All required metrics are exposed!"
    exit 0
else
    echo "✗ Some required metrics are missing"
    exit 1
fi
