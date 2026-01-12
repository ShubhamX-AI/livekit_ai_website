#!/bin/bash
set -e

echo "Starting deployment..."

echo "Pulling latest code..."
git pull origin master  # or 'main', as per your default branch

echo "Building and starting backend..."
docker compose up -d --build backend

echo "Waiting for backend to become healthy..."
for i in {1..15}; do
  STATUS=$(docker inspect --format='{{.State.Health.Status}}' livekit_ai_website-backend-1 2>/dev/null || echo "starting")
  if [ "$STATUS" = "healthy" ]; then
    echo "Backend is healthy."
    break
  fi
  sleep 2
done

if [ "$STATUS" != "healthy" ]; then
  echo "Backend failed health check. Aborting deployment."
  exit 1
fi

echo "Building and starting frontend..."
docker compose up -d --build frontend

echo "Cleaning unused containers..."
docker container prune -f

echo "Cleaning unused images..."
docker image prune -f

echo "Cleaning unused networks..."
docker network prune -f

echo "Deployment completed successfully."