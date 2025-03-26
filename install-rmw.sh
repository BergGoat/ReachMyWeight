#!/bin/bash

# ReachMyWeight Complete Installation Script
# Usage: curl -fsSL https://raw.githubusercontent.com/BergGoat/ReachMyWeight/main/install-rmw.sh | bash
set -e

echo "🚀 Setting up ReachMyWeight stack with advanced monitoring..."

# Ask for credentials if not provided as environment variables
if [ -z "$DEPLOY_API_KEY" ]; then
    read -sp "Enter Deployment API Key: " DEPLOY_API_KEY
    echo ""
fi

if [ -z "$DOCKER_USERNAME" ]; then
    read -p "Enter Docker Hub Username: " DOCKER_USERNAME
fi

if [ -z "$DOCKER_PASSWORD" ]; then
    read -sp "Enter Docker Hub Password/Token: " DOCKER_PASSWORD
    echo ""
fi

if [ -z "$GRAFANA_PASSWORD" ]; then
    GRAFANA_PASSWORD=$(openssl rand -base64 12)
    echo "Generated Grafana admin password: $GRAFANA_PASSWORD"
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

# Update Grafana password
if [ -f "RMW-Monitoring/grafana/config.monitoring" ]; then
    echo "🔑 Updating Grafana credentials..."
    sed -i "s/^GF_SECURITY_ADMIN_PASSWORD=.*/GF_SECURITY_ADMIN_PASSWORD=$GRAFANA_PASSWORD/" RMW-Monitoring/grafana/config.monitoring
else
    echo "📝 Creating Grafana config file..."
    mkdir -p RMW-Monitoring/grafana
    cat > RMW-Monitoring/grafana/config.monitoring << EOF
GF_SECURITY_ADMIN_PASSWORD=$GRAFANA_PASSWORD
GF_USERS_ALLOW_SIGN_UP=false
EOF
fi

# Create/update environment file for deployment service
echo "📝 Creating deployment environment file..."
cat > .env.deployment << EOF
DEPLOY_API_KEY=$DEPLOY_API_KEY
DOCKER_USERNAME=$DOCKER_USERNAME
DOCKER_PASSWORD=$DOCKER_PASSWORD
EOF

# Deploy the application stack
echo "📦 Deploying main application stack..."
docker stack deploy -c RMW-Deployment/docker-stack.yml --with-registry-auth rmw

# Create external network if it doesn't exist
if ! docker network ls | grep -q "rmw-network"; then
    echo "🌐 Creating rmw-network..."
    docker network create --driver overlay rmw-network
fi

# Update network name in the monitoring stack if needed
if grep -q "monitor-net" RMW-Monitoring/docker-stack.yml; then
    echo "🔧 Updating network name in monitoring stack..."
    sed -i 's/monitor-net/rmw-network/g' RMW-Monitoring/docker-stack.yml
fi

# Deploy the monitoring stack
echo "📦 Deploying monitoring stack..."
docker stack deploy -c RMW-Monitoring/docker-stack.yml monitoring

echo "✅ ReachMyWeight installation complete!"
echo "Frontend: http://localhost:80"
echo "Backend API: http://localhost:8001"
echo "Database API: http://localhost:8002"
echo "Deployment Service: http://localhost:8080"
echo ""
echo "✅ Advanced Monitoring stack installed!"
echo "Grafana: http://localhost:3000 (admin/password: $GRAFANA_PASSWORD)"
echo "Prometheus: http://localhost:9090"
echo "AlertManager: http://localhost:9093"
echo "cAdvisor: http://localhost:8082"
echo "Node Exporter: http://localhost:9100"
echo ""
echo "You can check stack status with: docker stack services rmw"
echo "You can check monitoring status with: docker stack services monitoring" 