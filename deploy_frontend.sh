#!/bin/bash
set -e

echo "Starting deployment..."

echo "Pulling latest code..."

git pull origin master

echo "Building and starting services..."

docker compose -f docker-compose-frontend.yml up -d --build --wait

echo "Cleaning up..."

docker system prune -f

echo "Deployment completed successfully."