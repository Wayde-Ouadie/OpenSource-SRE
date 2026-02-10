#!/usr/bin/env bash
# Export OpenAPI specs from each running service.
# Usage: ./scripts/export-openapi.sh
#
# Requires services to be running (make up).
set -euo pipefail

DOCS_DIR="docs/openapi"
mkdir -p "$DOCS_DIR"

echo "==> Exporting OpenAPI specs..."

services=(
  "incident-management:8002"
  "alert-ingestion:8001"
  "oncall-service:8003"
  "notification-service:8004"
  "gateway:8000"
)

for entry in "${services[@]}"; do
  name="${entry%%:*}"
  port="${entry##*:}"

  echo -n "  $name... "
  if curl -sf "http://localhost:$port/openapi.json" -o "$DOCS_DIR/$name.openapi.json" 2>/dev/null; then
    echo "✓ saved to $DOCS_DIR/$name.openapi.json"
  else
    echo "⊘ skipped (service not reachable on port $port)"
  fi
done

echo
echo "✓ OpenAPI export complete. Files in $DOCS_DIR/"
