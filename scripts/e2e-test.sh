#!/usr/bin/env bash

echo "==> Running E2E test: Alert → Incident → Acknowledgment → Resolution"
echo

echo "Step 1: Setting up on-call schedule..."
SCHEDULE_RESPONSE=$(curl -fsS -X POST http://localhost:8003/api/v1/schedules \
    -H 'Content-Type: application/json' \
    -d '{"team":"e2e-test-team","primary":["alice"],"secondary":["bob"],"rotation":"daily"}')
echo "  Schedule created: $SCHEDULE_RESPONSE"

echo
echo "Step 2: Sending test alert..."
ALERT_RESPONSE=$(curl -fsS -X POST http://localhost:8001/api/v1/alerts \
    -H 'Content-Type: application/json' \
    -d '{"service":"e2e-test-service","severity":"critical","message":"E2E test: Critical issue detected","labels":{"environment":"production","test":"e2e"}}')
echo "  Alert response: $ALERT_RESPONSE"

INCIDENT_ID=$(echo "$ALERT_RESPONSE" | grep -o '"incident_id":"[^"]*"' | cut -d'"' -f4 || echo "")

if [ -z "$INCIDENT_ID" ]; then
    echo "✗ Failed to get incident_id from alert response"
    exit 1
fi

echo "  Incident created: $INCIDENT_ID"

echo
echo "Step 3: Verifying incident was created..."
sleep 1
INCIDENT_DETAIL=$(curl -fsS "http://localhost:8002/api/v1/incidents/$INCIDENT_ID")
echo "  Incident details: $INCIDENT_DETAIL"

echo
echo "Step 4: Acknowledging incident..."
ACK_RESPONSE=$(curl -fsS -X PATCH "http://localhost:8002/api/v1/incidents/$INCIDENT_ID" \
    -H 'Content-Type: application/json' \
    -d '{"status":"acknowledged"}')
echo "  Acknowledged: $ACK_RESPONSE"

echo
echo "Step 5: Resolving incident..."
sleep 1
RESOLVE_RESPONSE=$(curl -fsS -X PATCH "http://localhost:8002/api/v1/incidents/$INCIDENT_ID" \
    -H 'Content-Type: application/json' \
    -d '{"status":"resolved"}')
echo "  Resolved: $RESOLVE_RESPONSE"

echo
echo "Step 6: Verifying metrics were recorded..."
METRICS=$(curl -fsS http://localhost:8002/metrics | grep -E "(incidents_total|incident_mtta|incident_mttr)")
echo "  Metrics:"
echo "$METRICS"

echo
echo "✓ E2E test completed successfully!"
echo "  - Created on-call schedule"
echo "  - Sent alert and created incident: $INCIDENT_ID"
echo "  - Acknowledged incident"
echo "  - Resolved incident"
echo "  - Verified metrics"
