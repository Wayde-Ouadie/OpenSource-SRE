#!/usr/bin/env bash

echo "==> Building all container images..."

docker-compose -f deployment/docker-compose.yml build

echo "✓ All images built successfully!"
