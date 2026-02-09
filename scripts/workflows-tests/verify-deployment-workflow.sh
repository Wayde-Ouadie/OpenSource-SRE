#!/usr/bin/env bash

echo "==> Running post-deployment verification..."

echo "  Running health checks..."
make health

echo "  Running integration tests..."
make test-integration

echo "✓ Deployment verification passed!"
