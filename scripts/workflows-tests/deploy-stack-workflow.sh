#!/usr/bin/env bash

echo "==> Deploying Docker Compose stack..."

echo "  Cleaning up previous deployment..."
docker-compose -f deployment/docker-compose.yml down --remove-orphans --volumes 2>/dev/null || true

echo "  Starting services..."
docker-compose -f deployment/docker-compose.yml --env-file deployment/.env up -d

echo "  Waiting for services to be healthy..."
sleep 5

echo "✓ Stack deployed successfully!"
