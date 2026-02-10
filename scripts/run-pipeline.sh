#!/usr/bin/env bash
set -euo pipefail

stage() {
  echo
  echo "==> $1"
}

stage "Stage 1/7: Quality"
python -m compileall -q \
  "incident-management-service" \
  alert-ingestion-service \
  oncall-service \
  notification-service \
  gateway-service

# Run Ruff linter
if command -v ruff >/dev/null 2>&1 || pip install ruff >/dev/null 2>&1; then
  ruff check incident-management-service/ alert-ingestion-service/ oncall-service/ notification-service/ gateway-service/ --config pyproject.toml
fi

( cd web-ui-service && npm ci && npm run build )

stage "Stage 2/7: Security (secrets)"
if command -v docker >/dev/null 2>&1; then
  docker run --rm -v "$PWD:/repo" zricethezav/gitleaks:latest detect --source=/repo --no-git
else
  echo "docker not found; skipping secret scan"
fi

stage "Stage 3/7: Build"
make build

stage "Stage 4/7: Scan (images)"
if command -v docker >/dev/null 2>&1; then
  # Trivy is optional; skip if you want faster runs
  if [ "${SKIP_SCAN:-0}" = "1" ]; then
    echo "SKIP_SCAN=1; skipping image scan"
  else
    echo "Scanning images with Trivy (can take a bit on first run)"
    docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:0.49.1 version >/dev/null
    # Keep this skeleton simple: scan a representative service image if present
    for img in ims/oncall:local ims/alert-ingestion:local ims/notification:local; do
      if docker image inspect "$img" >/dev/null 2>&1; then
        docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:0.49.1 image --severity HIGH,CRITICAL --exit-code 1 "$img"
      fi
    done
  fi
else
  echo "docker not found; skipping image scan"
fi

stage "Stage 5/7: Test"
make test-unit

stage "Stage 6/7: Deploy"
make down || true
make up

stage "Stage 7/7: Verify"
make health
make verify

echo
echo "Pipeline OK"
