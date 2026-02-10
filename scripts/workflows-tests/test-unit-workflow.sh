#!/usr/bin/env bash
set -euo pipefail

echo "=== Stage 5: Unit Tests ==="

SERVICES=(
    incident-management-service
    alert-ingestion-service
    oncall-service
    notification-service
    gateway-service
)

pip install --quiet pytest pytest-cov httpx 2>/dev/null

FAILED=0

for svc in "${SERVICES[@]}"; do
    echo ""
    echo "--- Testing $svc ---"

    if [ ! -d "$svc/tests" ]; then
        echo "  ⚠ No tests/ directory — skipping"
        continue
    fi

    # Install service dependencies (skip psycopg2 in CI — tests use SQLite)
    pip install --quiet -r "$svc/requirements.txt" 2>/dev/null || true

    (cd "$svc" && python -m pytest tests/ -v --tb=short) || {
        echo "  ✗ $svc tests FAILED"
        FAILED=1
    }
done

echo ""
if [ "$FAILED" -eq 0 ]; then
    echo "✓ All unit tests passed!"
else
    echo "✗ Some tests failed!"
    exit 1
fi
