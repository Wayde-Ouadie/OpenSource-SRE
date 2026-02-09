#!/usr/bin/env bash
# Load test: Send multiple alerts to test alert correlation
set -euo pipefail

echo "==> Running load test: Multiple alerts"
echo

NUM_ALERTS=${1:-10}
SERVICE="load-test-service"
SEVERITY="high"

echo "Sending $NUM_ALERTS alerts to service '$SERVICE' with severity '$SEVERITY'"
echo "Testing alert correlation (should group alerts within 5-minute window)..."
echo

for i in $(seq 1 "$NUM_ALERTS"); do
    echo -n "  Alert $i/$NUM_ALERTS... "
    RESPONSE=$(curl -fsS -X POST http://localhost:8001/api/v1/alerts \
        -H 'Content-Type: application/json' \
        -d "{\"service\":\"$SERVICE\",\"severity\":\"$SEVERITY\",\"message\":\"Load test alert #$i\",\"labels\":{\"test\":\"load\",\"index\":$i}}")
    
    INCIDENT_ID=$(echo "$RESPONSE" | grep -o '"incident_id":"[^"]*"' | cut -d'"' -f4 || echo "")
    ACTION=$(echo "$RESPONSE" | grep -o '"action":"[^"]*"' | cut -d'"' -f4 || echo "")
    
    echo "→ $INCIDENT_ID ($ACTION)"
    
    # Small delay between alerts
    sleep 0.1
done

echo
echo "Load test complete. Checking results..."
sleep 1

# Count incidents with our test service
INCIDENTS=$(curl -fsS "http://localhost:8002/api/v1/incidents?service=$SERVICE")
INCIDENT_COUNT=$(echo "$INCIDENTS" | grep -o '"id"' | wc -l)

echo
echo "Results:"
echo "  Alerts sent: $NUM_ALERTS"
echo "  Incidents created: $INCIDENT_COUNT"
echo
if [ "$INCIDENT_COUNT" -lt "$NUM_ALERTS" ]; then
    echo "✓ Alert correlation working! (Multiple alerts grouped into fewer incidents)"
else
    echo "⚠ Warning: Each alert created a separate incident (correlation may not be working)"
fi

# Show metrics
echo
echo "Alert metrics:"
curl -fsS http://localhost:8001/metrics | grep -E "alerts_(received|correlated)_total"
