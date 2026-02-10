#!/usr/bin/env bash
# Workflow Test: Code Quality Check
# This script runs syntax checks and builds for all services
set -euo pipefail

echo "==> Running code quality checks (syntax + build)..."

# Python services syntax check
echo "  Checking Python syntax..."
python3 -m compileall -q \
  "incident-management-service" \
  alert-ingestion-service \
  oncall-service \
  notification-service \
  gateway-service

# Web UI build check
echo "  Building web-ui..."
cd web-ui-service
npm install
npm run build
cd ..

echo "✓ Quality checks passed!"
