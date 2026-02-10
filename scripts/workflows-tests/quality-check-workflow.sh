#!/usr/bin/env bash
# Workflow Test: Code Quality Check
# This script runs syntax checks, linting, and builds for all services
set -euo pipefail

echo "==> Running code quality checks (syntax + lint + build)..."

# Python services syntax check
echo "  Checking Python syntax..."
python3 -m compileall -q \
  "incident-management-service" \
  alert-ingestion-service \
  oncall-service \
  notification-service \
  gateway-service

# Python linting with Ruff
echo "  Running Ruff linter..."
if ! command -v ruff >/dev/null 2>&1; then
    pip install ruff >/dev/null 2>&1 || true
fi
if command -v ruff >/dev/null 2>&1; then
    ruff check incident-management-service/ alert-ingestion-service/ oncall-service/ notification-service/ gateway-service/ --config pyproject.toml
fi

# Web UI build check
echo "  Building web-ui..."
cd web-ui-service
npm install
npm run build
cd ..

echo "✓ Quality checks passed!"
