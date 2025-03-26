#!/bin/bash

# ReachMyWeight Complete Installation Script
# Usage: curl -fsSL https://raw.githubusercontent.com/BergGoat/ReachMyWeight/main/install-rmw.sh | bash
set -e

echo "🚀 Setting up ReachMyWeight stack with advanced monitoring..."

# Ask for deployment API key
if [ -z "$DEPLOY_API_KEY" ]; then
    read -sp "Enter Deployment API Key (for redeploy endpoint): " DEPLOY_API_KEY
    echo ""
fi

# Check requirements
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check for swarm mode
if ! docker node ls &> /dev/null; then
    echo "❌ Docker swarm not initialized. Initializing now..."
    docker swarm init
fi

# Clone repository if not already present
if [ ! -d "ReachMyWeight" ]; then
    echo "📦 Cloning ReachMyWeight repository..."
    git clone https://github.com/BergGoat/ReachMyWeight.git
    cd ReachMyWeight
else
    echo "📂 Using existing ReachMyWeight directory..."
    cd ReachMyWeight
    git pull
fi

# Check for existing stacks and remove them to ensure clean installation
echo "🔍 Checking for existing stacks..."

# Remove monitoring stack if it exists
if docker stack ls | grep -q "monitoring"; then
    echo "🧹 Removing existing monitoring stack..."
    docker stack rm monitoring
fi

# Remove rmw stack if it exists
if docker stack ls | grep -q "rmw"; then
    echo "🧹 Removing existing rmw stack..."
    docker stack rm rmw
fi

# Wait for stacks to be fully removed
echo "⏱️ Waiting for stacks to be fully removed..."
sleep 20

# Clean up all volumes related to the stacks
echo "🧹 Cleaning up all related volumes..."
# Find and remove any matching volumes
for vol in $(docker volume ls --format "{{.Name}}" | grep -E 'monitoring_|rmw_|grafana_data|prometheus_data'); do
    echo "  Removing volume: $vol"
    docker volume rm $vol || true
done

# Create external network if it doesn't exist
if ! docker network ls | grep -q "rmw-network"; then
    echo "🌐 Creating rmw-network..."
    docker network create --driver overlay rmw-network
fi

# Create/update environment file for deployment service (API key only)
echo "📝 Creating deployment environment file..."
cat > RMW-Deployment/.env.deployment << EOF
DEPLOY_API_KEY=$DEPLOY_API_KEY
EOF

# Update network name in the monitoring stack if needed
if grep -q "monitor-net" RMW-Monitoring/docker-stack.yml; then
    echo "🔧 Updating network name in monitoring stack..."
    sed -i 's/monitor-net/rmw-network/g' RMW-Monitoring/docker-stack.yml
fi

# Deploy the application stack
echo "📦 Deploying main application stack..."
docker stack deploy -c RMW-Deployment/docker-stack.yml --with-registry-auth rmw

# Deploy the monitoring stack
echo "📦 Deploying monitoring stack (Prometheus, Grafana, Alertmanager, Node Exporter, cAdvisor)..."
docker stack deploy -c RMW-Monitoring/docker-stack.yml monitoring

echo "✅ ReachMyWeight installation complete!"
echo ""
echo "Main Application:"
echo "----------------"
echo "Frontend: http://localhost:80"
echo "Backend API: http://localhost:8001"
echo "Database API: http://localhost:8002"
echo "Deployment Service: http://localhost:8080"
echo ""
echo "Monitoring:"
echo "----------"
echo "Grafana: http://localhost:3000 (admin/admin)"
echo "Prometheus: http://localhost:9090"
echo "AlertManager: http://localhost:9093"
echo "cAdvisor: http://localhost:8082"
echo "Node Exporter: http://localhost:9100"
echo ""
echo "You can check stack status with:"
echo "docker stack services rmw        # Application services"
echo "docker stack services monitoring # Monitoring services" 