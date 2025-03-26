#!/bin/bash

# ReachMyWeight Complete Installation Script
# Usage: curl -fsSL https://gist.githubusercontent.com/BergGoat/95e9f0be1e33487706dfe73942500329/raw/69b2a92b9a7afdf1b8bbb287b055df1d46fdbb64/install-rmw.sh | bash
set -e

echo "🚀 Setting up ReachMyWeight stack with advanced monitoring..."

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

# Create temp directory
TEMP_DIR=$(mktemp -d)
cd $TEMP_DIR

# Create directories
mkdir -p RMW-Monitoring/prometheus
mkdir -p RMW-Monitoring/alertmanager
mkdir -p RMW-Monitoring/grafana/provisioning/datasources
mkdir -p RMW-Monitoring/grafana/provisioning/dashboards

# Create prometheus.yml
cat > RMW-Monitoring/prometheus/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - 'alert.rules'

alerting:
  alertmanagers:
  - scheme: http
    static_configs:
    - targets:
      - alertmanager:9093

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
  
  - job_name: 'rmw_backend'
    static_configs:
      - targets: ['rmw_backend:8001']
    
  - job_name: 'rmw_frontend'
    static_configs:
      - targets: ['rmw_frontend:8000']
    
  - job_name: 'rmw_database'
    static_configs:
      - targets: ['rmw_database:8002']
    
  - job_name: 'rmw_deployment'
    static_configs:
      - targets: ['rmw_deployment:8080']
    
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']

  - job_name: 'cadvisor'
    static_configs:
      - targets: ['cadvisor:8080']
EOF

# Create prometheus alert rules
cat > RMW-Monitoring/prometheus/alert.rules << 'EOF'
groups:
- name: targets
  rules:
  - alert: monitor_service_down
    expr: up == 0
    for: 30s
    labels:
      severity: critical
    annotations:
      summary: "Monitor service non-operational"
      description: "Service {{ $labels.instance }} is down."

- name: host
  rules:
  - alert: high_cpu_load
    expr: node_load1 > 1.5
    for: 30s
    labels:
      severity: warning
    annotations:
      summary: "Server under high load"
      description: "Docker host is under high load, the avg load 1m is at {{ $value}}. Reported by instance {{ $labels.instance }} of job {{ $labels.job }}."

  - alert: high_memory_load
    expr: (sum(node_memory_MemTotal_bytes) - sum(node_memory_MemFree_bytes + node_memory_Buffers_bytes + node_memory_Cached_bytes) ) / sum(node_memory_MemTotal_bytes) * 100 > 85
    for: 30s
    labels:
      severity: warning
    annotations:
      summary: "Server memory is almost full"
      description: "Docker host memory usage is {{ humanize $value}}%. Reported by instance {{ $labels.instance }} of job {{ $labels.job }}."

  - alert: high_storage_load
    expr: (node_filesystem_size_bytes{fstype="aufs"} - node_filesystem_free_bytes{fstype="aufs"}) / node_filesystem_size_bytes{fstype="aufs"}  * 100 > 85
    for: 30s
    labels:
      severity: warning
    annotations:
      summary: "Server storage is almost full"
      description: "Docker host storage usage is {{ humanize $value}}%. Reported by instance {{ $labels.instance }} of job {{ $labels.job }}."
EOF

# Create Alertmanager config
cat > RMW-Monitoring/alertmanager/config.yml << 'EOF'
route:
  receiver: 'slack'

receivers:
  - name: 'slack'
    slack_configs:
      - send_resolved: true
        username: 'Alertmanager'
        channel: '#alerts'
        api_url: 'https://hooks.slack.com/services/TOKEN/TOKEN/TOKEN'
EOF

# Create grafana datasource
cat > RMW-Monitoring/grafana/provisioning/datasources/datasources.yml << 'EOF'
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
EOF

# Create grafana.monitoring config file
cat > RMW-Monitoring/grafana/config.monitoring << 'EOF'
GF_SECURITY_ADMIN_PASSWORD=ReachMyWeight321
GF_USERS_ALLOW_SIGN_UP=false
EOF

# Create main docker-stack.yml for RMW application
cat > docker-stack.yml << 'EOF'
version: '3.8'

services:
  rmw_deployment:
    image: steelduck1/rmw-deployment:latest
    ports:
      - "8080:8080"
    environment:
      - DEPLOY_API_KEY=Belastingdienst321!
      - DOCKER_USERNAME=steelduck1
      - DOCKER_PASSWORD=dckr_pat_kGDJWvFImSRa5a5auIM5m0a2zLR1
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    deploy:
      replicas: 1
      restart_policy:
        condition: any
      update_config:
        parallelism: 1
        delay: 10s
        order: start-first
    networks:
      - rmw-network

  rmw_frontend:
    image: steelduck1/rmw-frontend:latest
    ports:
      - "80:8000"
    environment:
      - DATABASE_API_URL=http://rmw_database:8002
      - ORIGINAL_API_URL=http://rmw_backend:8001
    deploy:
      replicas: 2
      restart_policy:
        condition: any
      update_config:
        parallelism: 1
        delay: 10s
        order: start-first
    networks:
      - rmw-network

  rmw_backend:
    image: steelduck1/rmw-backend:latest
    ports:
      - "8001:8001"
    environment:
      - DATABASE_API_URL=http://rmw_database:8002
    deploy:
      replicas: 2
      restart_policy:
        condition: any
      update_config:
        parallelism: 1
        delay: 10s
        order: start-first
    networks:
      - rmw-network
    depends_on:
      - rmw_database

  rmw_database:
    image: steelduck1/rmw-database:latest
    ports:
      - "8002:8002"
    environment:
      - SQLITE_CONNECTION_PARAMS=check_same_thread=False
    deploy:
      replicas: 1
      restart_policy:
        condition: any
      update_config:
        parallelism: 1
        delay: 10s
        order: start-first
    volumes:
      - rmw_database_data:/app/data
    networks:
      - rmw-network

networks:
  rmw-network:
    driver: overlay
    external: false

volumes:
  rmw_database_data:
EOF

# Create separate stack file for monitoring
cat > monitoring-stack.yml << 'EOF'
version: '3.7'

services:
  prometheus:
    image: prom/prometheus:v2.36.2
    volumes:
      - ./RMW-Monitoring/prometheus/:/etc/prometheus/
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/usr/share/prometheus/console_libraries'
      - '--web.console.templates=/usr/share/prometheus/consoles'
      - '--web.enable-lifecycle'
      - '--web.enable-admin-api'
    ports:
      - 9090:9090
    depends_on:
      - cadvisor
    networks:
      - rmw-network
    deploy:
      placement:
        constraints:
          - node.role==manager
      restart_policy:
        condition: on-failure

  node-exporter:
    image: quay.io/prometheus/node-exporter:latest
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command: 
      - '--path.procfs=/host/proc' 
      - '--path.sysfs=/host/sys'
      - --collector.filesystem.ignored-mount-points
      - "^/(sys|proc|dev|host|etc|rootfs/var/lib/docker/containers|rootfs/var/lib/docker/overlay2|rootfs/run/docker/netns|rootfs/var/lib/docker/aufs)($$|/)"
    ports:
      - 9100:9100
    networks:
      - rmw-network
    deploy:
      mode: global
      restart_policy:
          condition: on-failure

  alertmanager:
    image: prom/alertmanager
    ports:
      - 9093:9093
    volumes:
      - "./RMW-Monitoring/alertmanager/:/etc/alertmanager/"
    networks:
      - rmw-network
    command:
      - '--config.file=/etc/alertmanager/config.yml'
      - '--storage.path=/alertmanager'
    deploy:
      placement:
        constraints:
           - node.role==manager
      restart_policy:
        condition: on-failure    

  cadvisor:
    image: gcr.io/cadvisor/cadvisor
    volumes:
      - /:/rootfs:ro
      - /var/run:/var/run:rw
      - /sys:/sys:ro
      - /var/lib/docker/:/var/lib/docker:ro
    ports:
      - 8082:8080  # Changed from 8080 to avoid conflict with rmw_deployment
    networks:
      - rmw-network
    deploy:
      mode: global
      restart_policy:
          condition: on-failure

  grafana:
    image: grafana/grafana
    depends_on:
      - prometheus
    ports:
      - 3000:3000
    volumes:
      - grafana_data:/var/lib/grafana
      - ./RMW-Monitoring/grafana/provisioning/:/etc/grafana/provisioning/
    env_file:
      - ./RMW-Monitoring/grafana/config.monitoring
    networks:
      - rmw-network
    user: "472"
    deploy:
      placement:
        constraints:
          - node.role==manager
      restart_policy:
        condition: on-failure

networks:
  rmw-network:
    external: true

volumes:
  prometheus_data: {}
  grafana_data: {}
EOF

# Deploy the application stack
echo "📦 Deploying main application stack..."
docker stack deploy -c docker-stack.yml rmw

# Deploy the monitoring stack
echo "📦 Deploying monitoring stack..."
docker stack deploy -c monitoring-stack.yml monitoring

# Save files to a permanent location
mkdir -p ~/rmw-stack
cp -r * ~/rmw-stack/
echo "💾 Configuration files saved to ~/rmw-stack/"

# Cleanup
cd - > /dev/null
rm -rf $TEMP_DIR

echo "✅ ReachMyWeight installation complete!"
echo "Frontend: http://localhost:80"
echo "Backend API: http://localhost:8001"
echo "Database API: http://localhost:8002"
echo "Deployment Service: http://localhost:8080"
echo ""
echo "✅ Advanced Monitoring stack installed!"
echo "Grafana: http://localhost:3000 (admin/ReachMyWeight321)"
echo "Prometheus: http://localhost:9090"
echo "AlertManager: http://localhost:9093"
echo "cAdvisor: http://localhost:8082"
echo "Node Exporter: http://localhost:9100"
echo ""
echo "You can check stack status with: docker stack services rmw"
echo "You can check monitoring status with: docker stack services monitoring" 