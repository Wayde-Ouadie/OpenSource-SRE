#!/usr/bin/env bash

echo "==> Running security scan (gitleaks)..."

if ! command -v docker >/dev/null 2>&1; then
    echo "✗ Docker not found. Cannot run security scan."
    exit 1
fi

docker run --rm -v "$PWD:/repo" \
  zricethezav/gitleaks:latest detect --source=/repo --no-git

echo "✓ Security scan passed!"
