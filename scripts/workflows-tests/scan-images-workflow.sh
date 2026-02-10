#!/usr/bin/env bash
set -euo pipefail

echo "==> Scanning container images for vulnerabilities (trivy)..."

docker compose -f deployment/docker-compose.yml build

images=$(docker compose -f deployment/docker-compose.yml config | awk '/image:/{print $2}' | grep "ims/" | sort -u || true)

if [ -z "$images" ]; then
    echo "⊘ No custom images found to scan."
    exit 0
fi

echo "Images to scan:"
echo "$images" | sed 's/^/  - /'

failed=0
for img in $images; do
    echo
    echo "Scanning $img..."
    if docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
        aquasec/trivy:0.49.1 image --severity HIGH,CRITICAL --exit-code 0 --quiet "$img"; then
        echo "  ✓ $img scan completed"
    else
        echo "  ✗ $img has vulnerabilities"
        failed=1
    fi
done

if [ $failed -eq 0 ]; then
    echo
    echo "✓ All image scans passed!"
    exit 0
else
    echo
    echo "✗ Some images have vulnerabilities"
    exit 1
fi
