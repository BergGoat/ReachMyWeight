#!/bin/bash

# ReachMyWeight All-in-One Deployment Script
# This script deploys the complete RMW stack including monitoring
set -e

echo "🚀 Deploying ReachMyWeight stack with monitoring..."

# Check if docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if in swarm mode
if ! docker node ls &> /dev/null; then
    echo "❌ Docker swarm not initialized. Initializing now..."
    docker swarm init
fi

# Deploy the stack using the root docker-stack.yml file
echo "📦 Deploying stack..."
docker stack deploy -c docker-stack.yml rmw

echo "✅ Deployment complete!"
echo "Frontend: http://localhost:80"
echo "Backend API: http://localhost:8001"
echo "Database API: http://localhost:8002"
echo "Deployment Service: http://localhost:8080"
echo "Grafana UI: http://localhost:3000 (admin/ReachMyWeight321)"
echo "Prometheus UI: http://localhost:9090"
echo ""
echo "You can check stack status with: docker stack services rmw" 