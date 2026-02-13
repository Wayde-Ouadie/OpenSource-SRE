#!/usr/bin/env bash

SERVICE_NAME="${1:?Service name required}"
CONTEXT="${2:?Context path required}"
DOCKERFILE="${3:?Dockerfile path required}"
TAG="${4:?Image tag required}"
PORT="${5:?Container port required}"
HEALTH_PATH="${6:-/health}"

echo "==> Building and testing service: $SERVICE_NAME"

echo "  Building image: $TAG"
docker build -t "$TAG" -f "$DOCKERFILE" "$CONTEXT"

echo "  Running smoke test..."
CONTAINER_NAME="${SERVICE_NAME}-ci-test"
HOST_PORT="18080"

cleanup() {
    echo "  Cleaning up..."
    docker logs "$CONTAINER_NAME" 2>/dev/null | tail -20 || true
    docker stop "$CONTAINER_NAME" 2>/dev/null || true
    docker rm "$CONTAINER_NAME" 2>/dev/null || true
}
trap cleanup EXIT

docker run -d --rm --name "$CONTAINER_NAME" \
    -p "$HOST_PORT:$PORT" \
    -e DATABASE_URL="sqlite:////tmp/smoke_test.db" \
    "$TAG"

URL="http://127.0.0.1:${HOST_PORT}${HEALTH_PATH}"
echo "  Waiting for health endpoint: $URL"

for i in {1..10}; do
    if curl -fsS --connect-timeout 2 --max-time 5 "$URL" >/dev/null 2>&1; then
        echo "  ✓ Health check passed!"
        exit 0
    fi
    echo "    Attempt $i/10..."
    sleep 1
done

echo "  ✗ Health check failed!"
exit 1
