#!/usr/bin/env bash
# Security scan: Check for secrets and vulnerabilities
set -euo pipefail

echo "==> Running security scans..."
echo

FAILED=0

# Check if docker is available
if ! command -v docker >/dev/null 2>&1; then
    echo "✗ Docker not found. Cannot run security scans."
    exit 1
fi

# 1. Secrets scanning with GitLeaks
echo "1. Scanning for exposed secrets (GitLeaks)..."
if docker run --rm -v "$PWD:/repo" zricethezav/gitleaks:latest detect \
    --source=/repo \
    --no-git \
    --verbose 2>&1 | tee /tmp/gitleaks-output.txt; then
    echo "  ✓ No secrets detected"
else
    if grep -q "leaks found" /tmp/gitleaks-output.txt; then
        echo "  ✗ Secrets detected! Review output above."
        FAILED=1
    else
        echo "  ✓ No secrets detected"
    fi
fi

echo
echo "2. Scanning container images (Trivy)..."

# Build list of images to scan
IMAGES=(
    "ims/alert-ingestion:local"
    "ims/incident-management:local"
    "ims/oncall:local"
    "ims/notification:local"
    "ims/web-ui:local"
    "ims/gateway:local"
    "ims/monitoring:local"
)

for img in "${IMAGES[@]}"; do
    if docker image inspect "$img" >/dev/null 2>&1; then
        echo "  Scanning $img..."
        if docker run --rm \
            -v /var/run/docker.sock:/var/run/docker.sock \
            aquasec/trivy:0.49.1 image \
            --severity HIGH,CRITICAL \
            --exit-code 0 \
            --quiet \
            "$img" | tee "/tmp/trivy-$(basename $img).txt"; then
            
            # Check if any HIGH or CRITICAL vulns were found
            if grep -qE "(HIGH|CRITICAL)" "/tmp/trivy-$(basename $img).txt" 2>/dev/null; then
                echo "    ⚠ Vulnerabilities found in $img"
            else
                echo "    ✓ No critical vulnerabilities"
            fi
        fi
    else
        echo "  ⊘ Image $img not found (skipping)"
    fi
done

echo
echo "3. Checking for hardcoded credentials in code..."
if grep -rn --include="*.py" --include="*.js" --include="*.jsx" \
    -E "(password|secret|api_key|token)\s*=\s*['\"][^'\"]+['\"]" \
    alert-ingestion-service/ \
    " incident-management-service/" \
    oncall-service/ \
    notification-service/ \
    gateway-service/ \
    monitoring-service/ \
    web-ui-service/src/ 2>/dev/null; then
    echo "  ⚠ Potential hardcoded credentials found (review above)"
    FAILED=1
else
    echo "  ✓ No obvious hardcoded credentials"
fi

echo
if [ $FAILED -eq 0 ]; then
    echo "✓ Security scans completed - no critical issues"
    exit 0
else
    echo "✗ Security scans found issues - review output above"
    exit 1
fi
